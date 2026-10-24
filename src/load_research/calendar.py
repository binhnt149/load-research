"""Versioned local calendars; no unverified built-in annual holiday list."""

import calendar as month_calendar
import hashlib
import json
import re
from collections import Counter
from datetime import date, timedelta
from enum import StrEnum


class DayType(StrEnum):
    WEEKDAY = "weekday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"
    HOLIDAY = "holiday"


def month_days(period: str) -> list[date]:
    if not re.fullmatch(r"\d{4}-\d{2}", period):
        raise ValueError("month must be YYYY-MM")
    first = date.fromisoformat(period + "-01")
    return [
        first + timedelta(days=i)
        for i in range(month_calendar.monthrange(first.year, first.month)[1])
    ]


class ResearchCalendar:
    def __init__(
        self,
        holidays: set[date] | None = None,
        overrides: dict[date, DayType] | None = None,
    ) -> None:
        self.holidays = frozenset(holidays or ())
        self.overrides = {day: DayType(kind) for day, kind in (overrides or {}).items()}

    def classify(self, day: date) -> DayType:
        if day in self.overrides:
            return self.overrides[day]
        if day in self.holidays:
            return DayType.HOLIDAY
        return {5: DayType.SATURDAY, 6: DayType.SUNDAY}.get(
            day.weekday(), DayType.WEEKDAY
        )

    def counts(self, period: str) -> dict[DayType, int]:
        counts = Counter(self.classify(day) for day in month_days(period))
        return {kind: counts[kind] for kind in DayType}

    def to_dict(self) -> dict:
        return {
            "holidays": sorted(day.isoformat() for day in self.holidays),
            "overrides": {
                day.isoformat(): kind.value
                for day, kind in sorted(self.overrides.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ResearchCalendar":
        return cls(
            {date.fromisoformat(day) for day in payload.get("holidays", [])},
            {
                date.fromisoformat(day): DayType(kind)
                for day, kind in payload.get("overrides", {}).items()
            },
        )

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()
