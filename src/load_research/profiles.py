"""Customer-first representative curves from a shared monthly cohort."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np

from load_research.calendar import DayType, ResearchCalendar, month_days
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Customer
from load_research.quality import MonthQuality


@dataclass
class CustomerProfile:
    customer: Customer
    period: str
    day_type: DayType
    values: np.ndarray
    days_used: int = 1
    estimated_fraction: float = 0.0
    unknown_fraction: float = 0.0


@dataclass
class ProfileSelection:
    profiles: list[CustomerProfile]
    excluded: dict[str, str]


def select_profiles(
    months: Iterable[MonthQuality],
    calendar: ResearchCalendar,
    config: RunConfig,
    *,
    on_selected: Callable[[MonthQuality], None] | None = None,
) -> ProfileSelection:
    profiles, excluded = [], {}
    minimum = dict(zip(DayType, config.min_days, strict=True))
    for month in months:
        identifier = month.customer.customer_id
        if month.original_coverage < config.min_original_coverage:
            excluded[identifier] = "insufficient_original_coverage"
            continue
        if config.vee_completion == "complete" and any(
            not np.isfinite(day.values).all() for day in month.days
        ):
            excluded[identifier] = "incomplete_vee"
            continue
        dates = month_days(month.period)
        counts = calendar.counts(month.period)
        present = [kind for kind in DayType if counts[kind] > 0]
        usable = {
            kind: [
                day
                for index, day in enumerate(month.days)
                if day.eligible and calendar.classify(dates[index]) == kind
            ]
            for kind in present
        }
        missing = [
            kind.value
            for kind in present
            if len(usable[kind]) < min(minimum[kind], counts[kind])
        ]
        if missing:
            excluded[identifier] = "insufficient_day_types:" + ",".join(missing)
            continue
        if on_selected is not None:
            on_selected(month)
        for kind in present:
            days = usable[kind]
            values = np.stack([day.values for day in days]).mean(axis=0)
            slots = len(days) * len(values)
            profiles.append(
                CustomerProfile(
                    month.customer,
                    month.period,
                    kind,
                    values,
                    len(days),
                    sum(int(day.estimated.sum()) for day in days) / slots,
                    sum(day.unknown_count for day in days) / slots,
                )
            )
    profiles.sort(
        key=lambda profile: (
            profile.customer.industry_code,
            profile.period,
            profile.day_type.value,
            profile.customer.customer_id,
        )
    )
    return ProfileSelection(profiles, excluded)
