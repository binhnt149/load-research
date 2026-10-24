from datetime import date

import pytest

from load_research.calendar import DayType, ResearchCalendar


def test_leap_year_calendar_and_nonexistent_holidays():
    calendar = ResearchCalendar()
    counts = calendar.counts("2024-02")
    assert sum(counts.values()) == 29
    assert counts[DayType.HOLIDAY] == 0
    assert counts[DayType.SATURDAY] == 4


def test_override_has_precedence_over_holiday_and_weekend():
    day = date(2024, 2, 10)
    calendar = ResearchCalendar(holidays={day}, overrides={day: DayType.WEEKDAY})
    assert calendar.classify(day) == DayType.WEEKDAY
    assert ResearchCalendar(holidays={day}).classify(day) == DayType.HOLIDAY


def test_calendar_version_changes_when_a_day_changes():
    assert (
        ResearchCalendar().content_hash
        != ResearchCalendar(holidays={date(2024, 1, 1)}).content_hash
    )


@pytest.mark.parametrize("period", ["2024-13", "2024-2", "02", "../x"])
def test_invalid_month_is_rejected(period):
    with pytest.raises(ValueError):
        ResearchCalendar().counts(period)
