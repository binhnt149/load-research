"""Canonical active-import intervals, with explicit engineering semantics."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

from load_research.domain.config import SourceOptions
from load_research.domain.energy import energy_from_value, interval_start
from load_research.importers.catalog import Catalog, number, required_text


@dataclass(frozen=True)
class MeterRecord:
    customer_id: str
    industry_code: str
    meter_id: str
    start: datetime
    minutes: int
    energy_kwh: float | None
    estimated: bool
    quality_known: bool
    source_id: str
    source_row: int
    repair_blocked: bool = False


def _measurements(
    row: dict, options: SourceOptions
) -> Iterator[tuple[str | datetime, str, int]]:
    if options.layout == "long":
        field = (
            "interval_end"
            if options.timestamp_convention == "end"
            else "interval_start"
        )
        timestamp = row.get("timestamp") or row.get(field)
        if not timestamp:
            raise ValueError("missing interval timestamp")
        yield timestamp, row.get("value", ""), 0
        return
    day = datetime.fromisoformat(required_text(row, "date"))
    if day.hour or day.minute or day.second or day.tzinfo:
        raise ValueError("wide row date must be a local calendar date")
    for index in range(1440 // options.interval_minutes):
        field = f"{options.slot_prefix}{index + 1:02}"
        if field not in row:
            raise ValueError(f"missing wide interval column {field}")
        offset = index + (options.timestamp_convention == "end")
        yield (
            day + timedelta(minutes=offset * options.interval_minutes),
            row[field],
            index + 1,
        )


def canonicalize(
    rows: Iterable[dict],
    catalog: Catalog,
    options: SourceOptions,
    *,
    source_id: str = "source",
    issues: list[dict] | None = None,
) -> Iterator[MeterRecord]:
    for index, row in enumerate(rows, start=2):
        row_number = int(row.get("_source_row", index))
        context: dict = {
            "source_id": source_id,
            "source_row": row_number,
            "source_slot": None,
            "policy": "reject_entire_row",
        }
        try:
            if row.get("organization_code", catalog.scope) != catalog.scope:
                raise ValueError("MDMS scope differs from study scope")
            if row.get("channel", options.channel) != options.channel:
                raise ValueError("MDMS channel differs from declared import channel")
            if (
                row.get("interval_minutes")
                and int(row["interval_minutes"]) != options.interval_minutes
            ):
                raise ValueError(
                    "MDMS resolution differs from declared source resolution"
                )
            if row.get("unit") and row["unit"] != options.unit:
                raise ValueError("MDMS unit differs from declared source unit")
            if row.get("direction") and row["direction"] not in (
                "import",
                "import_active",
            ):
                raise ValueError("MDMS direction is not active import")
            if (
                row.get("measurement_kind")
                and row["measurement_kind"] != options.measurement_kind
            ):
                raise ValueError(
                    "MDMS measurement kind differs from source declaration"
                )
            meter_id = str(
                row.get("meter_id") or row.get("measurement_point_id") or ""
            ).strip()
            if not meter_id:
                raise ValueError("missing meter mapping key")
            quality = str(row.get("source_quality_flag", "unknown")).lower().strip()
            estimated = quality in ("estimated", "substituted", "e", "s")
            known = estimated or quality in ("measured", "actual", "valid", "a")
            interruption = quality in ("outage", "shutdown", "do_not_estimate")
            declared_block = str(row.get("repair_blocked", "")).strip().lower()
            if declared_block not in ("", "0", "1", "false", "true", "no", "yes"):
                raise ValueError("repair_blocked must be an explicit boolean")
            interruption |= declared_block in ("1", "true", "yes")
            known |= interruption
            records = []  # a wide row is committed atomically; at most 96 intervals
            for timestamp, raw, slot in _measurements(row, options):
                context["source_slot"] = slot or None
                start = interval_start(
                    timestamp,
                    options.interval_minutes,
                    options.timestamp_convention,
                    options.timezone,
                    options.timestamp_format,
                ).replace(tzinfo=None)
                if options.layout == "long":
                    for field, convention in (
                        ("interval_start", "start"),
                        ("interval_end", "end"),
                    ):
                        if row.get(field):
                            declared = interval_start(
                                row[field],
                                options.interval_minutes,
                                convention,
                                options.timezone,
                                options.timestamp_format,
                            ).replace(tzinfo=None)
                            if declared != start:
                                raise ValueError(
                                    "MDMS interval boundaries contradict declared duration/timestamp"
                                )
                customer = catalog.resolve(meter_id, start)
                if (
                    row.get("customer_id")
                    and row["customer_id"] != customer.customer_id
                ):
                    raise ValueError("customer id contradicts meter mapping")
                missing = str(raw).strip() == "" or quality in ("invalid", "missing")
                energy = (
                    None
                    if missing
                    else energy_from_value(
                        number(raw, decimal=options.decimal),
                        options.unit,
                        options.measurement_kind,
                        options.interval_minutes,
                        bool(options.values_already_scaled),
                        options.multiplier,
                    )
                )
                records.append(
                    MeterRecord(
                        customer.customer_id,
                        customer.industry_code,
                        meter_id,
                        start,
                        options.interval_minutes,
                        energy,
                        estimated,
                        known,
                        source_id,
                        row_number,
                        interruption,
                    )
                )
            yield from records
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            if issues is None:
                raise ValueError(f"invalid source row {row_number}: {error}") from error
            issues.append({**context, "reason": str(error)})
