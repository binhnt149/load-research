"""Conservative repairs with immutable source arrays and per-value provenance."""

from dataclasses import dataclass, field

import numpy as np

from load_research.calendar import ResearchCalendar, month_days
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Customer
from load_research.infrastructure.store import MonthGrid


@dataclass
class DayQuality:
    values: np.ndarray
    estimated: np.ndarray
    original_valid: int
    unknown_count: int
    adjustments: list[dict]
    eligible: bool


def gaps(values: np.ndarray) -> list[tuple[int, int]]:
    missing = ~np.isfinite(values)
    changes = np.diff(np.r_[False, missing, False].astype(int))
    return list(
        zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1), strict=True)
    )


def day_eligible(values: np.ndarray, estimated: np.ndarray, config: RunConfig) -> bool:
    return bool(
        np.isfinite(values).all()
        and estimated.sum() / len(values) <= config.max_estimated_fraction
    )


def repair_day(
    values: np.ndarray,
    config: RunConfig,
    *,
    estimated: np.ndarray | None = None,
    quality_known: np.ndarray | None = None,
    repair_blocked: np.ndarray | None = None,
) -> DayQuality:
    original = np.asarray(values, dtype=float)
    if (
        original.shape != (1440 // config.interval_minutes,)
        or np.isinf(original).any()
        or (original < 0).any()
    ):
        raise ValueError("invalid daily energy grid")
    repaired = original.copy()
    estimate_mask = (
        np.zeros(len(original), bool)
        if estimated is None
        else np.asarray(estimated, dtype=bool).copy()
    )
    known = (
        np.ones(len(original), bool)
        if quality_known is None
        else np.asarray(quality_known, dtype=bool)
    )
    blocked = (
        np.zeros(len(original), bool)
        if repair_blocked is None
        else np.asarray(repair_blocked, dtype=bool)
    )
    if (
        estimate_mask.shape != original.shape
        or known.shape != original.shape
        or blocked.shape != original.shape
    ):
        raise ValueError("quality mask shape differs from energy grid")
    adjustments = []
    for start, end in gaps(original):
        if (
            start == 0
            or end == len(original)
            or (end - start) * config.interval_minutes > config.max_linear_minutes
            or blocked[max(0, start - 1) : min(len(original), end + 1)].any()
        ):
            continue
        interpolated = np.linspace(original[start - 1], original[end], end - start + 2)[
            1:-1
        ]
        for slot, value in zip(range(start, end), interpolated, strict=True):
            repaired[slot] = value
            estimate_mask[slot] = True
            adjustments.append(
                {
                    "slot_index": slot + 1,
                    "old": None,
                    "new": float(value),
                    "method": "linear",
                }
            )
    return DayQuality(
        repaired,
        estimate_mask,
        int(np.isfinite(original).sum()),
        int((~known & np.isfinite(original)).sum()),
        adjustments,
        day_eligible(repaired, estimate_mask, config),
    )


@dataclass
class MonthQuality:
    customer: Customer
    period: str
    days: list[DayQuality]
    original_coverage: float
    adjustments: list[dict]
    diagnostics: dict = field(default_factory=dict)


def statistical_warnings(
    values: np.ndarray, *, factor: float = 6, min_days: int = 3
) -> dict:
    """Original observations only; warnings never alter or exclude an observation."""
    values = np.asarray(values, dtype=float)
    complete = np.isfinite(values).all(axis=1)
    result: dict = {
        "mad_status": "insufficient_days",
        "mad_outliers": 0,
        "mad_supported_slots": 0,
        "zero_days": int((complete & (np.nansum(values, axis=1) == 0)).sum()),
        "flat_days": int(sum(np.ptp(row) == 0 for row in values[complete])),
    }
    if len(values) < min_days:
        return result
    for column in values.T:
        observed = column[np.isfinite(column)]
        if len(observed) < min_days:
            continue
        median = np.median(observed)
        mad = np.median(np.abs(observed - median))
        if mad > 0:
            result["mad_supported_slots"] += 1
            result["mad_outliers"] += int(
                (np.abs(observed - median) > factor * mad).sum()
            )
    result["mad_status"] = (
        "available"
        if result["mad_supported_slots"]
        else "zero_mad_or_insufficient_observations"
    )
    return result


def repair_month(
    grid: MonthGrid, calendar: ResearchCalendar, config: RunConfig
) -> MonthQuality:
    dates = month_days(grid.period)
    if grid.values.shape != (len(dates), 1440 // config.interval_minutes):
        raise ValueError("invalid customer-month grid")
    original = grid.values
    blocked = (
        np.zeros_like(original, bool)
        if grid.repair_blocked is None
        else grid.repair_blocked
    )
    kinds = [calendar.classify(day) for day in dates]
    repaired = [
        repair_day(
            row,
            config,
            estimated=grid.estimated[index],
            quality_known=grid.quality_known[index],
            repair_blocked=blocked[index],
        )
        for index, row in enumerate(original)
    ]
    for index, day in enumerate(repaired):
        for start, end in gaps(day.values):
            if (
                end - start
            ) * config.interval_minutes > config.max_like_minutes or blocked[
                index, max(0, start - 1) : min(len(day.values), end + 1)
            ].any():
                continue
            donors = [
                candidate
                for candidate in range(len(dates))
                if candidate != index
                and kinds[candidate] == kinds[index]
                and np.isfinite(original[candidate, start:end]).all()
                and not grid.estimated[candidate, start:end].any()
                and not blocked[candidate].any()
            ]
            if len(donors) < config.min_donors:
                continue
            donor_values = original[donors]
            valid_donors = np.isfinite(donor_values) & ~grid.estimated[donors]
            typical = np.ma.median(
                np.ma.array(donor_values, mask=~valid_donors), axis=0
            ).filled(np.nan)
            common = np.isfinite(original[index]) & np.isfinite(typical)
            common &= ~blocked[index] & ~grid.estimated[index]
            if common.sum() < len(day.values) * config.donor_common_fraction:
                continue
            denominator = float(typical[common].sum())
            if denominator <= 0:
                continue
            factor = float(original[index, common].sum()) / denominator
            if not config.donor_scale_min <= factor <= config.donor_scale_max:
                continue
            for slot in range(start, end):
                value = float(typical[slot] * factor)
                day.values[slot] = value
                day.estimated[slot] = True
                day.adjustments.append(
                    {
                        "slot_index": slot + 1,
                        "old": None,
                        "new": value,
                        "method": "like_day",
                        "scale_factor": factor,
                        "donor_dates": [dates[source].isoformat() for source in donors],
                    }
                )
        day.eligible = day_eligible(day.values, day.estimated, config)
    adjustments = [
        {
            **event,
            "customer_id": grid.customer.customer_id,
            "date": dates[index].isoformat(),
        }
        for index, day in enumerate(repaired)
        for event in day.adjustments
    ]
    diagnostics = {
        kind.value: statistical_warnings(
            np.where(grid.estimated, np.nan, original)[np.asarray(kinds) == kind],
            factor=config.mad_factor,
            min_days=config.mad_min_days,
        )
        for kind in set(kinds)
    }
    return MonthQuality(
        grid.customer,
        grid.period,
        repaired,
        float(np.isfinite(original).sum() / original.size),
        adjustments,
        diagnostics,
    )
