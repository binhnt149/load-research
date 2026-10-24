import numpy as np

from load_research.domain.config import RunConfig
from load_research.quality import repair_day


def config():
    return RunConfig(periods=("2024-02",), scope="NPC")


def test_short_interior_gap_is_interpolated_and_audited():
    values = np.ones(48)
    values[4:6] = np.nan
    result = repair_day(values, config())
    assert np.allclose(result.values, 1)
    assert result.eligible
    assert len(result.adjustments) == 2
    assert result.adjustments[0]["method"] == "linear"
    assert np.isnan(values[4])  # source remains unchanged


def test_edges_long_gaps_and_whole_missing_days_are_not_invented():
    for missing in (slice(0, 1), slice(5, 8), slice(0, 48)):
        values = np.ones(48)
        values[missing] = np.nan
        result = repair_day(values, config())
        assert not result.eligible
        assert np.isnan(result.values).any()


def test_valid_zero_and_real_peak_are_retained():
    assert repair_day(np.zeros(48), config()).eligible
    values = np.ones(48)
    values[10] = 100000
    result = repair_day(values, config())
    assert result.eligible
    assert result.values[10] == 100000
    assert result.adjustments == []


def test_known_source_estimates_count_towards_daily_budget():
    estimated = np.zeros(48, bool)
    estimated[:5] = True
    result = repair_day(np.ones(48), config(), estimated=estimated)
    assert not result.eligible
    assert result.original_valid == 48


def test_mad_warnings_preserve_valid_peaks():
    from load_research.quality import statistical_warnings

    values = np.tile(np.arange(1, 49, dtype=float), (8, 1))
    values[:, 3] = [9, 10, 11, 10, 9, 10, 11, 100]
    before = values.copy()
    warnings = statistical_warnings(values, factor=6)
    assert warnings["mad_outliers"] == 1
    np.testing.assert_array_equal(values, before)
    assert (
        statistical_warnings(np.zeros((2, 48)), factor=6)["mad_status"]
        == "insufficient_days"
    )


def test_known_interruption_blocks_interpolation():
    values = np.ones(48)
    values[4] = np.nan
    blocked = np.zeros(48, bool)
    blocked[4] = True
    result = repair_day(values, config(), repair_blocked=blocked)
    assert np.isnan(result.values[4])
    assert not result.eligible
