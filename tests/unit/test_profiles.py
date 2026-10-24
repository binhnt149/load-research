from dataclasses import replace

import numpy as np
import pytest

from load_research.calendar import DayType, ResearchCalendar, month_days
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Customer
from load_research.infrastructure.store import MonthGrid
from load_research.profiles import select_profiles
from load_research.quality import repair_month


def month(customer_id, values, config, calendar):
    source = MonthGrid(
        Customer(customer_id, "01"),
        "2024-02",
        values,
        np.zeros_like(values, bool),
        np.ones_like(values, bool),
    )
    return repair_month(source, calendar, config)


def test_customer_missing_sundays_is_excluded_from_every_day_type():
    calendar = ResearchCalendar()
    config = RunConfig(periods=("2024-02",), scope="NPC")
    good, missing = np.ones((29, 48)), np.ones((29, 48))
    for index, day in enumerate(month_days("2024-02")):
        if calendar.classify(day) == DayType.SUNDAY:
            missing[index] = np.nan
    selection = select_profiles(
        [month("001", good, config, calendar), month("002", missing, config, calendar)],
        calendar,
        config,
    )
    assert {profile.customer.customer_id for profile in selection.profiles} == {"001"}
    assert "002" in selection.excluded
    assert len(selection.profiles) == 3  # February has no holiday in this calendar


def test_each_customer_is_averaged_before_aggregation():
    calendar = ResearchCalendar()
    config = replace(
        RunConfig(periods=("2024-02",), scope="NPC"), min_original_coverage=0.5
    )
    first = np.ones((29, 48))
    second = np.full((29, 48), 2.0)
    weekdays = [
        index
        for index, day in enumerate(month_days("2024-02"))
        if calendar.classify(day) == DayType.WEEKDAY
    ]
    second[weekdays[:6]] = np.nan
    selection = select_profiles(
        [month("001", first, config, calendar), month("002", second, config, calendar)],
        calendar,
        config,
    )
    profiles = [
        profile for profile in selection.profiles if profile.day_type == DayType.WEEKDAY
    ]
    assert len(profiles) == 2
    assert [profile.values.sum() for profile in profiles] == pytest.approx([48, 96])
    assert profiles[0].days_used != profiles[1].days_used
