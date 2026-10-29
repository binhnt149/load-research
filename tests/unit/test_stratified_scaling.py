import numpy as np
import pytest

from load_research.calendar import DayType
from load_research.clustering import ClusterResult
from load_research.importers.catalog import Customer
from load_research.profiles import CustomerProfile
from load_research.stratified_scaling import allocate_monthly_by_reference, scale_strata


def stratum(customer_id, shape):
    profiles = [
        CustomerProfile(Customer(customer_id, "01"), "2026-01", kind, np.array(values))
        for kind, values in shape.items()
    ]
    groups = {
        kind: ClusterResult({customer_id: "unclassified"}, {}, {}) for kind in shape
    }
    return profiles, groups


def test_allocate_industry_month_using_reference_energy_ratios():
    totals = allocate_monthly_by_reference(1000, {"A": 100, "B": 300})
    assert totals == pytest.approx({"A": 250, "B": 750})
    assert sum(totals.values()) == pytest.approx(1000)


@pytest.mark.parametrize("reference", [{}, {"A": 0}, {"A": -1}, {"A": float("nan")}])
def test_allocation_needs_positive_valid_reference(reference):
    with pytest.raises(ValueError):
        allocate_monthly_by_reference(1000, reference)


def test_each_stratum_is_scaled_independently_and_sums_to_industry():
    counts = {DayType.WEEKDAY: 20, DayType.SUNDAY: 11}
    a = stratum("A1", {kind: [1.0] * 48 for kind in counts})
    b = stratum("B1", {kind: [2.0] * 48 for kind in counts})
    result = scale_strata(
        {"A": a, "B": b}, {"A": 1000, "B": 3000}, counts, min_customers=1
    )
    assert result.status == "valid"
    for code, target in (("A", 1000), ("B", 3000)):
        assert sum(
            counts[k] * v.sum() for k, v in result.strata[code].energy.items()
        ) == pytest.approx(target)
    assert sum(counts[k] * v.sum() for k, v in result.energy.items()) == pytest.approx(
        4000
    )
    assert np.allclose(
        result.energy[DayType.WEEKDAY],
        result.strata["A"].energy[DayType.WEEKDAY]
        + result.strata["B"].energy[DayType.WEEKDAY],
    )


def test_missing_billing_or_samples_cannot_create_complete_industry():
    counts = {DayType.WEEKDAY: 31}
    a = stratum("A1", {DayType.WEEKDAY: [1.0] * 48})
    missing_billing = scale_strata({"A": a}, {"A": None}, counts, min_customers=1)
    assert missing_billing.status == "incomplete"
    assert missing_billing.energy == {}
    missing_sample = scale_strata(
        {"A": a}, {"A": 1000, "B": 1000}, counts, min_customers=1
    )
    assert missing_sample.status == "incomplete"
    assert missing_sample.strata["B"].status == "no_eligible_samples"
    assert missing_sample.energy == {}


def test_customer_cannot_be_counted_in_two_strata():
    counts = {DayType.WEEKDAY: 31}
    a = stratum("same", {DayType.WEEKDAY: [1.0] * 48})
    with pytest.raises(ValueError, match="multiple strata"):
        scale_strata({"A": a, "B": a}, {"A": 1000, "B": 1000}, counts, min_customers=1)


def test_preview_status_is_not_promoted_to_valid():
    counts = {DayType.WEEKDAY: 31}
    a = stratum("A1", {DayType.WEEKDAY: [1.0] * 48})
    result = scale_strata({"A": a}, {"A": 1000}, counts, min_customers=2)
    assert result.status == "preview_insufficient_samples"
    assert result.energy[DayType.WEEKDAY].sum() * 31 == pytest.approx(1000)


def test_strata_from_different_industries_are_rejected():
    counts = {DayType.WEEKDAY: 31}
    a = stratum("A1", {DayType.WEEKDAY: [1.0] * 48})
    b = stratum("B1", {DayType.WEEKDAY: [1.0] * 48})
    b[0][0].customer = Customer("B1", "02")
    with pytest.raises(ValueError, match="one industry-month"):
        scale_strata({"A": a, "B": b}, {"A": 1000, "B": 1000}, counts, min_customers=1)
