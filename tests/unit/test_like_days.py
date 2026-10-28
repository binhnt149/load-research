import numpy as np
import pytest

from load_research.calendar import DayType, ResearchCalendar, month_days
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Customer
from load_research.infrastructure.store import MonthGrid
from load_research.quality import repair_month


def grid(values, estimated=None):
    return MonthGrid(
        Customer("001", "01"),
        "2024-02",
        values,
        np.zeros_like(values, bool) if estimated is None else estimated,
        np.ones_like(values, bool),
    )


def test_like_days_fill_only_bounded_gaps_using_original_same_type_days():
    values = np.ones((29, 48))
    values[0, 5:9] = np.nan
    repaired = repair_month(
        grid(values), ResearchCalendar(), RunConfig(periods=("2024-02",), scope="NPC")
    )
    assert repaired.days[0].eligible
    assert np.allclose(repaired.days[0].values, 1)
    events = [event for event in repaired.adjustments if event["method"] == "like_day"]
    assert len(events) == 4
    assert len(events[0]["donor_dates"]) >= 3


def test_holiday_without_donors_and_entire_missing_day_remain_missing():
    values = np.ones((29, 48))
    values[0, 5:9] = np.nan
    values[1] = np.nan
    calendar = ResearchCalendar(holidays={month_days("2024-02")[0]})
    repaired = repair_month(
        grid(values),
        calendar,
        RunConfig(periods=("2024-02",), scope="NPC", vee_completion="legacy"),
    )
    assert not repaired.days[0].eligible
    assert not repaired.days[1].eligible
    assert np.isnan(repaired.days[0].values[5:9]).all()
    assert np.isnan(repaired.days[1].values).all()


def test_repaired_values_cannot_be_used_as_new_donors():
    dates = month_days("2024-02")
    calendar = ResearchCalendar(
        overrides={
            day: DayType.WEEKDAY if index < 4 else DayType.HOLIDAY
            for index, day in enumerate(dates)
        }
    )
    values = np.ones((29, 48))
    values[0, 5:9] = np.nan
    values[1:4, 5] = np.nan
    repaired = repair_month(
        grid(values), calendar, RunConfig(periods=("2024-02",), scope="NPC")
    )
    assert all(repaired.days[index].eligible for index in (1, 2, 3))
    assert not repaired.days[0].eligible


def test_excessive_like_day_scaling_is_not_applied():
    values = np.ones((29, 48))
    values[0] = 3
    values[0, 5:9] = np.nan
    repaired = repair_month(
        grid(values), ResearchCalendar(), RunConfig(periods=("2024-02",), scope="NPC")
    )
    assert not repaired.days[0].eligible


def test_like_day_scaling_parameters_roundtrip_and_validate():
    config = RunConfig(
        periods=("2024-02",),
        scope="NPC",
        donor_scale_min=0.8,
        donor_scale_max=1.2,
        donor_common_fraction=0.75,
    )
    assert RunConfig.from_dict(config.to_dict()) == config
    with pytest.raises(ValueError):
        RunConfig(
            periods=("2024-02",), scope="NPC", donor_scale_min=2, donor_scale_max=1
        )
