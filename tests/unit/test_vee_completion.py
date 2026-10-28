from dataclasses import replace

import numpy as np

from load_research.calendar import ResearchCalendar, month_days
from load_research.domain.config import RunConfig
from load_research.importers.catalog import Customer
from load_research.infrastructure.store import MonthGrid
from load_research.profiles import select_profiles
from load_research.quality import repair_month


def month_grid(values, blocked=None):
    return MonthGrid(
        Customer("001", "01"),
        "2024-02",
        values,
        np.zeros_like(values, bool),
        np.ones_like(values, bool),
        np.zeros_like(values, bool) if blocked is None else blocked,
    )


def test_complete_vee_fills_whole_day_from_original_same_type_days_and_audits():
    values = np.tile(np.arange(1, 49, dtype=float), (29, 1))
    values[0, :] = np.nan
    original = values.copy()
    calendar = ResearchCalendar()
    config = RunConfig(periods=("2024-02",), scope="NPC")
    repaired = repair_month(month_grid(values), calendar, config)
    np.testing.assert_array_equal(repaired.days[0].values, np.arange(1, 49))
    assert repaired.days[0].estimated.all()
    assert len(repaired.adjustments) == 48
    assert {event["method"] for event in repaired.adjustments} == {"same_type_unscaled"}
    assert len(repaired.adjustments[0]["donor_dates"]) >= 3
    np.testing.assert_array_equal(values, original)
    assert select_profiles([repaired], calendar, config).profiles


def test_remaining_gaps_are_filled_without_changing_observed_values():
    values = np.ones((29, 48))
    values[0, :3] = np.nan
    values[0, 10:20] = np.nan
    calendar = ResearchCalendar()
    config = RunConfig(periods=("2024-02",), scope="NPC")
    repaired = repair_month(month_grid(values), calendar, config)
    assert np.isfinite(np.stack([d.values for d in repaired.days])).all()
    assert np.all(repaired.days[0].values == 1)
    assert repaired.days[0].estimated.sum() == 13


def test_missing_blocked_slot_excludes_customer_instead_of_inventing_data():
    values = np.ones((29, 48))
    blocked = np.zeros_like(values, bool)
    values[0, 5] = np.nan
    blocked[0, 5] = True
    calendar = ResearchCalendar()
    config = RunConfig(periods=("2024-02",), scope="NPC")
    repaired = repair_month(month_grid(values, blocked), calendar, config)
    assert np.isnan(repaired.days[0].values[5])
    selection = select_profiles([repaired], calendar, config)
    assert selection.profiles == []
    assert selection.excluded["001"] == "incomplete_vee"


def test_gap_adjacent_to_known_outage_is_not_filled_from_other_days():
    values = np.ones((29, 48))
    blocked = np.zeros_like(values, bool)
    values[0, 4] = 0
    values[0, 5:7] = np.nan
    blocked[0, 4] = True
    calendar = ResearchCalendar()
    config = RunConfig(periods=("2024-02",), scope="NPC")
    repaired = repair_month(month_grid(values, blocked), calendar, config)
    assert np.isnan(repaired.days[0].values[5:7]).all()
    assert (
        select_profiles([repaired], calendar, config).excluded["001"]
        == "incomplete_vee"
    )


def test_no_same_type_sources_leaves_missing_and_excludes_customer():
    values = np.ones((29, 48))
    values[0] = np.nan
    calendar = ResearchCalendar(holidays={month_days("2024-02")[0]})
    config = RunConfig(periods=("2024-02",), scope="NPC")
    repaired = repair_month(month_grid(values), calendar, config)
    assert np.isnan(repaired.days[0].values).all()
    assert (
        select_profiles([repaired], calendar, config).excluded["001"]
        == "incomplete_vee"
    )


def test_old_saved_config_keeps_legacy_vee_and_new_config_roundtrips():
    config = RunConfig(periods=("2024-02",), scope="NPC")
    assert config.vee_completion == "complete"
    assert RunConfig.from_dict(config.to_dict()) == config
    old = config.to_dict()
    del old["vee_completion"]
    legacy = RunConfig.from_dict(old)
    assert legacy.vee_completion == "legacy"
    values = np.ones((29, 48))
    values[0] = np.nan
    assert np.isnan(
        repair_month(month_grid(values), ResearchCalendar(), legacy).days[0].values
    ).all()
    assert replace(config, vee_completion="legacy") == legacy
