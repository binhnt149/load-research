import numpy as np
import pytest

from load_research.daily import DailyAccumulator, expand_daily
from load_research.result_view import ResultSelection


def cell():
    return {
        "industry_code": "01",
        "year_month": "2024-04",
        "result": {
            "billing_kwh": 144,
            "energy": {"weekday": [1] * 48, "saturday": [2] * 48},
        },
    }


def data(complete=True):
    return {
        "dates": ["2024-04-01", "2024-04-06"],
        "day_types": ["weekday", "saturday"],
        "cohort_size": 2,
        "source": [[1] * 48, [2] * 48],
        "processed": [[2] * 48, [4] * 48],
        "eligible": [True, complete],
    }


def test_calendar_model_repeats_day_type_and_variation_uses_one_monthly_factor():
    selection = ResultSelection("2024-04", ("01",), unit="kWh")
    calendar = expand_daily(cell(), data(), selection, method="representative")
    variation = expand_daily(cell(), data(), selection, method="variation")
    assert calendar["expanded"] == [[1] * 48, [2] * 48]
    assert variation["factor"] == pytest.approx(0.5)
    assert variation["expanded"] == calendar["expanded"]
    assert variation["monthly_energy_kwh"] == pytest.approx(144)


def test_variation_preserves_day_variation_instead_of_representative_shape():
    daily = data()
    daily["processed"] = [[1] * 48, [5] * 48]
    variation = expand_daily(
        cell(), daily, ResultSelection("2024-04", unit="kWh"), method="variation"
    )
    assert variation["expanded"] == [[0.5] * 48, [2.5] * 48]
    assert variation["monthly_energy_kwh"] == 144


def test_ineligible_cohort_day_blocks_monthly_factor_without_zero_filling():
    output = expand_daily(
        cell(), data(False), ResultSelection("2024-04"), method="variation"
    )
    assert output["factor"] is None and output["expanded"] == [None, None]
    assert output["reason"] == "incomplete_cohort_days"
    assert (
        expand_daily(
            cell(), data(False), ResultSelection("2024-04"), method="representative"
        )["expanded"][0]
        is not None
    )


@pytest.mark.parametrize(
    "billing,denominator,expected",
    [(0, 0, 0), (1, 0, None), (None, 1, None), (0, 1, 0)],
)
def test_zero_and_missing_energy_are_distinct(billing, denominator, expected):
    current = cell()
    current["result"]["billing_kwh"] = billing
    daily = data()
    daily["processed"] = [[denominator] * 48] * 2
    output = expand_daily(
        current, daily, ResultSelection("2024-04"), method="variation"
    )
    assert output["factor"] == expected
    if expected is None:
        assert output["expanded"] == [None, None]
    else:
        assert np.sum(output["expanded"]) == 0


def test_accumulation_propagates_missing_values_and_uses_customer_weights():
    accumulator = DailyAccumulator(2, 48)
    source = np.ones((2, 48))
    source[0, 0] = np.nan
    accumulator.add(source, np.ones((2, 48)) * 2, [True, True], 2)
    accumulator.add(np.ones((2, 48)), np.ones((2, 48)) * 3, [True, False], 1)
    output = accumulator.to_dict(["2024-04-01", "2024-04-06"], ["weekday", "saturday"])
    assert output["source"][0][0] is None
    assert output["source"][0][1] == 3
    assert output["processed"][0] == [7] * 48
    assert output["eligible"] == [True, False] and output["cohort_size"] == 2


def test_daily_resolution_conserves_energy_and_source_gaps():
    daily = data()
    daily["source"][0][0] = None
    output = expand_daily(
        cell(),
        daily,
        ResultSelection("2024-04", interval_minutes=60, unit="kWh"),
        method="representative",
    )
    assert output["source"][0][0] is None
    assert output["processed"][0] == [4] * 24
    assert output["expanded"][0] == [2] * 24
