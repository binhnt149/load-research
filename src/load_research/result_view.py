"""Pure, energy-first aggregation shared by screen and report output."""

import json
from dataclasses import dataclass

import numpy as np

from load_research.domain.energy import convert_curve
from load_research.presentation import DAY_TYPES


@dataclass(frozen=True)
class ResultSelection:
    period: str
    industry_codes: tuple[str, ...] = ()
    day_types: tuple[str, ...] = ()
    interval_minutes: int = 30
    unit: str = "kW"
    normalization: str | None = None
    scope: str = "industry_scaled"
    level: str = "industries"
    name: str = ""

    def __post_init__(self) -> None:
        if self.level not in ("industries", "component", "organization"):
            raise ValueError("invalid aggregation level")
        if self.scope not in ("industry_scaled", "sample_portfolio"):
            raise ValueError("invalid profile scope")
        if self.unit not in ("kW", "kWh") or self.interval_minutes not in (30, 60):
            raise ValueError("invalid output unit or resolution")
        if self.normalization not in (None, "mean", "share", "peak"):
            raise ValueError("unknown normalization")
        if set(self.day_types) - set(DAY_TYPES):
            raise ValueError("invalid day type")


def _vector(values: list, slots: int) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.shape != (slots,) or not np.isfinite(vector).all() or (vector < 0).any():
        raise ValueError("invalid interval energy")
    return vector


def build_result_view(result: dict, selection: ResultSelection) -> dict:
    """Missing industries block totals; available comparisons remain inspectable."""
    source = result["config"]["interval_minutes"]
    # Validate resolution even when no curves are available.
    convert_curve(
        [0] * (1440 // source), source, selection.interval_minutes, selection.unit
    )
    cells = {}
    for cell in result["cells"]:
        if cell["year_month"] == selection.period:
            code = cell["industry_code"]
            if code in cells:
                raise ValueError("duplicate industry month")
            cells[code] = cell
    universe = result.get("industry_universe", {}).get(selection.period)
    codes = sorted(
        set(
            (universe if universe is not None else cells)
            if selection.level == "organization" or not selection.industry_codes
            else selection.industry_codes
        )
    )
    available = [cells[code] for code in codes if code in cells]
    counts = available[0]["day_counts"] if available else {}
    if any(cell["day_counts"] != counts for cell in available):
        raise ValueError("inconsistent research calendar")
    kinds = [
        kind
        for kind in DAY_TYPES
        if counts.get(kind, 0) > 0
        and (not selection.day_types or kind in selection.day_types)
    ]
    days = sum(counts[kind] for kind in kinds)
    key = "energy" if selection.scope == "industry_scaled" else "sample"
    contribution_key = "contributions" if key == "energy" else "sample_contributions"
    series: list[dict] = []
    missing: list[dict] = []
    physical: dict[str, dict[str, np.ndarray]] = {}

    def append(kind: str, label: str, vector: np.ndarray | None, **metadata) -> None:
        converted = (
            None
            if vector is None
            else convert_curve(
                vector,
                source,
                selection.interval_minutes,
                selection.unit,
                selection.normalization,
            )
        )
        series.append(
            {
                "id": json.dumps([kind, metadata], sort_keys=True, ensure_ascii=False),
                "kind": kind,
                "label": label,
                "values": None if converted is None else converted.tolist(),
                **metadata,
            }
        )

    for code in codes:
        cell = cells.get(code)
        curves = {} if cell is None else cell["result"].get(key, {})
        absent = [kind for kind in kinds if kind not in curves]
        if cell is None or absent or not days:
            missing.append(
                {
                    "industry_code": code,
                    "day_types": absent,
                    "reason": "missing_profile",
                }
            )
            append("industry", code, None, industry_code=code)
            continue
        physical[code] = {kind: _vector(curves[kind], 1440 // source) for kind in kinds}
        weighted = sum(physical[code][kind] * counts[kind] / days for kind in kinds)
        append(
            "industry",
            f"{code} · {cell.get('industry_name', '')}",
            weighted,
            industry_code=code,
        )
        for kind in kinds:
            for cluster, values in (
                cell["result"].get(contribution_key, {}).get(kind, {}).items()
            ):
                name = cell.get("cluster_names", {}).get(kind, {}).get(cluster)
                if not name:
                    name = (
                        "Nhóm " + cluster.removeprefix("group_")
                        if cluster.startswith("group_")
                        else {
                            "inactive": "Không hoạt động",
                            "unclassified": "Chưa phân loại",
                            "not_segmented": "Chưa phân nhóm",
                        }.get(cluster, cluster)
                    )
                append(
                    "behavior",
                    f"{code} · {DAY_TYPES[kind]} · {name}",
                    _vector(values, 1440 // source) * counts[kind] / days,
                    industry_code=code,
                    day_type=kind,
                    cluster_id=cluster,
                )
    request = result.get("request")
    coverage_known = (
        selection.level != "organization"
        or universe is not None
        or (
            isinstance(request, dict)
            and "selected_industries" in request
            and not request["selected_industries"]
        )
    )
    if not coverage_known:
        missing.append({"industry_code": "", "reason": "unknown_industry_universe"})
    complete = bool(codes and days and not missing)
    combined = None
    if complete:
        by_day = {
            kind: np.sum([physical[code][kind] for code in codes], axis=0)
            for kind in kinds
        }
        combined = np.sum(
            [by_day[kind] * counts[kind] / days for kind in kinds], axis=0
        )
        if not np.isfinite(combined).all():
            raise ValueError("aggregate energy overflow")
        for kind in kinds:
            append(
                "day_type",
                DAY_TYPES[kind],
                by_day[kind],
                day_type=kind,
                day_count=counts[kind],
            )
    append(
        "overall",
        selection.name
        or ("Toàn đơn vị" if selection.level == "organization" else "Chung"),
        combined,
    )
    factors = [
        {
            "industry_code": code,
            **{
                field: cells[code]["result"].get(field)
                for field in ("alpha", "billing_kwh", "background_kwh")
            },
            "billing_basis": cells[code].get("billing_basis"),
            "status": cells[code]["result"].get("status"),
            "cohort_size": cells[code]["result"]
            .get("diagnostics", {})
            .get("cohort_size"),
        }
        for code in codes
        if code in cells
    ]
    billing = [row["billing_kwh"] for row in factors]
    return {
        "series": series,
        "complete": complete,
        "industry_codes": codes,
        "day_types": kinds,
        "day_count": days,
        "year_month": selection.period,
        "interval_minutes": selection.interval_minutes,
        "unit": "p.u." if selection.normalization else selection.unit,
        "physical_unit": selection.unit,
        "normalization": selection.normalization,
        "scope": selection.scope,
        "level": selection.level,
        "missing": missing,
        "factors": factors,
        "billing_kwh": sum(billing)
        if len(billing) == len(codes) and all(v is not None for v in billing)
        else None,
        "energy_selected_kwh": None
        if combined is None
        else float(combined.sum()) * days,
    }


def build_daily_view(
    result: dict, selection: ResultSelection, daily: dict, day: str, *, method: str
) -> dict:
    from dataclasses import replace
    from datetime import date

    from load_research.calendar import ResearchCalendar
    from load_research.daily import expand_daily, nullable
    from load_research.domain.energy import normalize

    calendar_day = date.fromisoformat(day)
    if calendar_day.strftime("%Y-%m") != selection.period:
        raise ValueError("date is outside the saved research periods")
    kind = (
        ResearchCalendar.from_dict(result.get("calendar", {}))
        .classify(calendar_day)
        .value
    )
    if selection.day_types and kind not in selection.day_types:
        raise ValueError("date does not match selected day type")
    if selection.normalization:
        view = build_daily_view(
            result,
            replace(selection, normalization=None, unit="kWh"),
            daily,
            day,
            method=method,
        )
        for row in view["series"]:
            values = row["values"]
            normalized = (
                None
                if values is None or any(v is None for v in values)
                else normalize(values, selection.normalization)
            )
            row["values"] = None if normalized is None else normalized.tolist()
        return {
            **view,
            "normalization": selection.normalization,
            "unit": "p.u.",
            "physical_unit": selection.unit,
        }
    view = build_result_view(result, selection)
    missing = [
        row for row in view["missing"] if row["reason"] == "unknown_industry_universe"
    ]
    series, selected_rows, source_rows, processed_rows, expanded_rows, factors = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    cells = {
        cell["industry_code"]: cell
        for cell in result["cells"]
        if cell["year_month"] == selection.period
    }
    for code in view["industry_codes"]:
        values = None
        details = daily.get(code)
        if details and code in cells and day in details["dates"]:
            expanded = expand_daily(cells[code], details, selection, method=method)
            index = details["dates"].index(day)
            source_rows.append(expanded["source"][index])
            processed_rows.append(expanded["processed"][index])
            expanded_rows.append(expanded["expanded"][index])
            values = expanded[
                "processed" if selection.scope == "sample_portfolio" else "expanded"
            ][index]
            factors.append(
                {
                    "industry_code": code,
                    "factor": expanded["factor"],
                    "reason": expanded["reason"],
                    "cohort_size": expanded["cohort_size"],
                    "eligible": expanded["eligible"][index],
                    "monthly_energy_kwh": expanded["monthly_energy_kwh"],
                }
            )
        if values is None or any(value is None for value in values):
            missing.append({"industry_code": code, "reason": "missing_daily_profile"})
        selected_rows.append(values)
        series.append(
            {
                "id": json.dumps(["industry", code]),
                "kind": "industry",
                "industry_code": code,
                "label": code,
                "values": values,
            }
        )

    def total(rows):
        if (
            len(rows) != len(view["industry_codes"])
            or not rows
            or any(row is None for row in rows)
        ):
            return None
        return nullable(np.sum(np.asarray(rows, dtype=float), axis=0))

    overall = total(selected_rows) if not missing else None
    series.insert(
        0,
        {
            "id": "overall",
            "kind": "overall",
            "label": selection.name or "Chung",
            "values": overall,
        },
    )
    series.extend(
        [
            {
                "id": "source",
                "kind": "source",
                "label": "Mẫu nguồn trước VEE",
                "values": total(source_rows),
            },
            {
                "id": "processed",
                "kind": "processed",
                "label": "Mẫu sau VEE",
                "values": total(processed_rows),
            },
        ]
    )
    if selection.scope == "sample_portfolio":
        series.append(
            {
                "id": "expanded",
                "kind": "expanded",
                "label": "Phụ tải suy rộng",
                "values": total(expanded_rows),
            }
        )
    energy = (
        None
        if overall is None
        else sum(overall)
        * (selection.interval_minutes / 60 if selection.unit == "kW" else 1)
    )
    return {
        **view,
        "series": series,
        "date": day,
        "method": method,
        "daily_factors": factors,
        "day_types": [kind],
        "missing": missing,
        "complete": overall is not None and not missing,
        "day_count": 1,
        "energy_selected_kwh": energy,
    }
