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
                name = cell.get("cluster_names", {}).get(kind, {}).get(cluster, cluster)
                append(
                    "behavior",
                    f"{code} · {DAY_TYPES[kind]} · {name}",
                    _vector(values, 1440 // source) * counts[kind] / days,
                    industry_code=code,
                    day_type=kind,
                    cluster_id=cluster,
                )
    coverage_known = not (
        selection.level == "organization"
        and universe is None
        and result.get("request", {}).get("selected_industries")
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
        "unit": selection.unit,
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
