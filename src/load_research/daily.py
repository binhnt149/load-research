"""Bounded daily cohort sums and two explicitly different expansion models."""

import numpy as np

from load_research.domain.energy import convert_curve
from load_research.result_view import ResultSelection


def nullable(vector: np.ndarray) -> list:
    return [float(value) if np.isfinite(value) else None for value in vector]


class DailyAccumulator:
    """One industry-month in memory, never a customer-year cube."""

    def __init__(self, days: int, slots: int) -> None:
        self.source = np.zeros((days, slots))
        self.processed = np.zeros((days, slots))
        self.eligible = np.ones(days, dtype=bool)
        self.cohort_size = 0

    def add(self, source, processed, eligible, weight: float) -> None:
        if not np.isfinite(weight) or weight <= 0:
            raise ValueError("weight must be positive")
        for values in (source, processed):
            if (
                np.shape(values) != self.source.shape
                or np.isinf(values).any()
                or (np.asarray(values) < 0).any()
            ):
                raise ValueError("invalid daily energy grid")
        if np.shape(eligible) != self.eligible.shape:
            raise ValueError("invalid daily eligibility")
        self.source += np.asarray(source) * weight
        self.processed += np.asarray(processed) * weight
        self.eligible &= eligible
        self.cohort_size += 1

    def to_dict(self, dates: list[str], kinds: list[str]) -> dict:
        return {
            "dates": dates,
            "day_types": kinds,
            "cohort_size": self.cohort_size,
            "source": [nullable(row) for row in self.source],
            "processed": [nullable(row) for row in self.processed],
            "eligible": self.eligible.tolist(),
        }


def expand_daily(
    cell: dict, daily: dict, selection: ResultSelection, *, method: str
) -> dict:
    if method not in ("representative", "variation"):
        raise ValueError("invalid daily expansion method")
    dates, kinds = daily["dates"], daily["day_types"]
    source = np.asarray(daily["source"], dtype=float)
    processed = np.asarray(daily["processed"], dtype=float)
    if (
        source.ndim != 2
        or processed.shape != source.shape
        or len(dates) != len(source)
        or len(kinds) != len(source)
    ):
        raise ValueError("invalid daily cohort shape")
    minutes = 1440 // source.shape[1]
    computed = cell["result"]
    billing = computed.get("billing_kwh")
    denominator = float(processed.sum())
    reason = None
    factor = None
    if billing is None:
        reason = "missing_billing"
    elif (
        not daily["cohort_size"]
        or not all(daily["eligible"])
        or not np.isfinite(processed).all()
    ):
        reason = "incomplete_cohort_days"
    elif denominator == 0 and billing > 0:
        reason = "zero_sample_with_positive_billing"
    else:
        factor = billing / denominator if denominator else 0.0
    raw_expanded: list[np.ndarray | None] = []
    for index, kind in enumerate(kinds):
        if method == "representative":
            values = computed.get("energy", {}).get(kind)
            raw_expanded.append(
                None if values is None else np.asarray(values, dtype=float)
            )
        else:
            raw_expanded.append(None if factor is None else processed[index] * factor)

    def convert(values):
        if values is None:
            return None
        if selection.normalization and not np.isfinite(values).all():
            return None
        vector = convert_curve(
            values,
            minutes,
            selection.interval_minutes,
            selection.unit,
            selection.normalization,
        )
        return None if vector is None else nullable(vector)

    complete = all(row is not None and np.isfinite(row).all() for row in raw_expanded)
    return {
        **{
            key: daily[key] for key in ("dates", "day_types", "cohort_size", "eligible")
        },
        "source": [convert(row) for row in source],
        "processed": [convert(row) for row in processed],
        "expanded": [convert(row) for row in raw_expanded],
        "method": method,
        "factor": factor if method == "variation" else computed.get("alpha"),
        "reason": reason
        if method == "variation"
        else (None if complete else "missing_profile"),
        "monthly_energy_kwh": sum(
            float(np.sum(row)) for row in raw_expanded if row is not None
        )
        if complete
        else None,
    }
