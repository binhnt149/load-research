from datetime import date

import numpy as np
import pytest

from load_research.domain.energy import (
    average_power_kw,
    energy_from_value,
    interval_start,
    normalize,
    resample_energy,
)


def test_30_minute_energy_aggregates_and_power_is_averaged():
    hourly = resample_energy(np.array([10.0, 20.0]), 30, 60)
    assert hourly.tolist() == [30.0]
    assert average_power_kw(hourly[0], 1.0) == 30.0
    assert average_power_kw(10, 0.5) == 20.0


def test_unknown_subinterval_is_not_treated_as_zero():
    result = resample_energy(np.array([10.0, np.nan, 20.0, 30.0]), 15, 30)
    assert np.isnan(result[0])
    assert result[1] == 50.0


def test_coarse_data_cannot_be_upsampled():
    with pytest.raises(ValueError, match="resolution"):
        resample_energy(np.ones(24), 60, 30)


@pytest.mark.parametrize("value", [-1, np.nan, np.inf])
def test_invalid_physical_energy_is_rejected(value):
    with pytest.raises(ValueError):
        average_power_kw(value, 0.5)


@pytest.mark.parametrize("duration", [0, -1, np.nan, np.inf])
def test_invalid_duration_is_rejected(duration):
    with pytest.raises(ValueError):
        average_power_kw(10, duration)


def test_units_and_transformer_multiplier_apply_once():
    assert energy_from_value(2, "MW", "interval_average_power", 30, False, 10) == 10000
    assert energy_from_value(2, "kWh", "interval_energy", 30, True, 10) == 2
    with pytest.raises(ValueError, match="measurement"):
        energy_from_value(2, "kW", "instantaneous", 30, True, 1)
    with pytest.raises(ValueError):
        energy_from_value(2, "kW", "interval_energy", 30, True, 1)


def test_end_stamped_midnight_belongs_to_previous_day():
    start = interval_start("2024-03-01T00:00:00", 30, "end")
    assert start.date() == date(2024, 2, 29)
    assert (start.hour, start.minute) == (23, 30)
    with pytest.raises(ValueError, match="aligned"):
        interval_start("2024-03-01T00:07:00", 30, "start")


@pytest.mark.parametrize(
    "raw,minutes,convention,expected",
    [
        ("2026-01-01T10:32:02", 30, "start", "2026-01-01T10:30:00+07:00"),
        ("2026-01-01T10:58:00", 30, "start", "2026-01-01T10:30:00+07:00"),
        ("2026-01-01T10:14:59", 15, "start", "2026-01-01T10:00:00+07:00"),
        ("2026-01-01T00:02:02", 30, "end", "2025-12-31T23:30:00+07:00"),
        ("2026-01-01T03:32:02+00:00", 30, "start", "2026-01-01T10:30:00+07:00"),
    ],
)
def test_floor_alignment_respects_source_interval_and_timestamp_convention(
    raw, minutes, convention, expected
):
    assert (
        interval_start(raw, minutes, convention, alignment="floor").isoformat()
        == expected
    )


def test_normalization_has_defined_sum_and_zero_is_not_a_shape():
    shape = np.array([1.0, 3.0, 2.0, 2.0])
    assert normalize(shape, "share").sum() == pytest.approx(1)
    assert normalize(shape, "mean").mean() == pytest.approx(1)
    assert normalize(shape, "peak").max() == 1
    assert normalize(np.zeros(48), "share") is None


def test_timezone_data_is_available_without_an_os_timezone_database():
    import zoneinfo
    from datetime import timedelta

    from load_research.domain.energy import interval_start

    original = zoneinfo.TZPATH
    try:
        zoneinfo.reset_tzpath(
            []
        )  # Windows and frozen applications need packaged tzdata
        zoneinfo.ZoneInfo.clear_cache()
        assert interval_start("2024-02-01T00:00", 30).utcoffset() == timedelta(hours=7)
    finally:
        zoneinfo.reset_tzpath(original)
        zoneinfo.ZoneInfo.clear_cache()
