import pytest

from load_research.daily import expand_daily
from load_research.result_view import ResultSelection


def test_daily_variation_scales_each_stratum_by_its_allocated_monthly_energy():
    def daily(levels):
        return {
            "dates": ["2026-01-01", "2026-01-02"],
            "day_types": ["weekday"] * 2,
            "cohort_size": 1,
            "eligible": [True, True],
            "source": [[v] * 48 for v in levels],
            "processed": [[v] * 48 for v in levels],
        }

    a, b = daily([1.0, 1.0]), daily([1.0, 3.0])
    total = daily([2.0, 4.0])
    total["cohort_size"] = 2
    total["strata"] = {"A": a, "B": b}
    cell = {
        "result": {"billing_kwh": 100, "energy": {}},
        "stratification": {
            "strata": {
                "A": {"allocated_billing_kwh": 25},
                "B": {"allocated_billing_kwh": 75},
            }
        },
    }
    result = expand_daily(
        cell, total, ResultSelection("2026-01", unit="kWh"), method="variation"
    )
    assert sum(result["expanded"][0]) == pytest.approx(31.25)
    assert sum(result["expanded"][1]) == pytest.approx(68.75)
    assert result["monthly_energy_kwh"] == pytest.approx(100)
    assert result["factor"] is None


def test_daily_variation_does_not_hide_missing_stratum():
    values = [[1.0] * 48]
    daily = {
        "dates": ["2026-01-01"],
        "day_types": ["weekday"],
        "cohort_size": 1,
        "eligible": [True],
        "source": values,
        "processed": values,
        "strata": {},
    }
    cell = {
        "result": {"billing_kwh": 100, "energy": {}},
        "stratification": {"strata": {"A": {"allocated_billing_kwh": 100}}},
    }
    result = expand_daily(
        cell, daily, ResultSelection("2026-01", unit="kWh"), method="variation"
    )
    assert result["expanded"] == [None]
    assert result["monthly_energy_kwh"] is None
