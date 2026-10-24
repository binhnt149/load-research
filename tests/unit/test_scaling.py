import numpy as np
import pytest

from load_research.calendar import DayType
from load_research.clustering import ClusterResult
from load_research.importers.catalog import Customer
from load_research.profiles import CustomerProfile
from load_research.scaling import scale_industry


def inputs():
    profiles = []
    for kind, level in ((DayType.WEEKDAY, 2), (DayType.SUNDAY, 1)):
        for identifier, factor in (("one", 1), ("noise", 2)):
            profiles.append(
                CustomerProfile(
                    Customer(identifier, "01"),
                    "2024-02",
                    kind,
                    np.full(48, level * factor),
                )
            )
    groups = {
        kind: ClusterResult({"one": "group_1", "noise": "unclassified"}, {}, {})
        for kind in (DayType.WEEKDAY, DayType.SUNDAY)
    }
    return profiles, groups, {DayType.WEEKDAY: 20, DayType.SUNDAY: 9}


def test_monthly_balance_preserves_day_type_levels_and_noise_contributions():
    profiles, groups, counts = inputs()
    result = scale_industry(profiles, groups, counts, 123456.0, min_customers=1)
    assert result.status == "valid"
    assert sum(
        counts[kind] * curve.sum() for kind, curve in result.energy.items()
    ) == pytest.approx(123456)
    assert result.energy[DayType.WEEKDAY].sum() / result.energy[
        DayType.SUNDAY
    ].sum() == pytest.approx(2)
    for kind, curve in result.energy.items():
        assert np.allclose(sum(result.contributions[kind].values()), curve)
        assert "unclassified" in result.contributions[kind]
    statistics = result.diagnostics["cluster_statistics"]["weekday"]["unclassified"]
    assert statistics["customers"] == 1
    assert statistics["sample_energy_share"] == pytest.approx(2 / 3)


def test_sample_weights_affect_energy_not_number_of_observation_days():
    profiles, groups, counts = inputs()
    profiles[0].customer = Customer("one", "01", 3)
    profiles[2].customer = Customer("one", "01", 3)
    result = scale_industry(profiles, groups, counts, 1000, min_customers=1)
    assert result.sample[DayType.WEEKDAY][0] == 10


def test_missing_zero_negative_billing_and_zero_shapes_have_distinct_status():
    profiles, groups, counts = inputs()
    assert (
        scale_industry(profiles, groups, counts, None, min_customers=1).status
        == "missing_billing"
    )
    with pytest.raises(ValueError):
        scale_industry(profiles, groups, counts, -1, min_customers=1)
    zero_target = scale_industry(profiles, groups, counts, 0, min_customers=1)
    assert zero_target.status == "valid_with_warnings"
    assert all(not curve.any() for curve in zero_target.energy.values())
    for profile in profiles:
        profile.values[:] = 0
    assert (
        scale_industry(profiles, groups, counts, 100, min_customers=1).status
        == "no_positive_shape"
    )
    assert scale_industry(profiles, groups, counts, 0, min_customers=1).alpha is None


def test_missing_day_type_or_different_cohort_cannot_be_scaled():
    profiles, groups, counts = inputs()
    with pytest.raises(ValueError, match="cohort"):
        scale_industry(profiles[:-1], groups, counts, 1000, min_customers=1)
