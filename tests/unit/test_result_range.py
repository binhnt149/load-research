import copy

import pytest
from test_result_aggregation import study

from load_research.result_range import build_range_view
from load_research.result_view import ResultSelection


def two_months():
    result = study()
    result["config"]["periods"] = ["2024-04", "2024-05"]
    for cell in copy.deepcopy(result["cells"]):
        cell["year_month"] = "2024-05"
        cell["result"]["energy"] = {
            k: [v * 3 for v in a] for k, a in cell["result"]["energy"].items()
        }
        cell["result"]["alpha"] *= 3
        cell["result"]["billing_kwh"] *= 3
        result["cells"].append(cell)
    result["industry_universe"]["2024-05"] = ["01", "02"]
    daily = {
        month: {
            code: {
                "dates": [day],
                "day_types": ["weekday"],
                "source": [[1] * 48],
                "processed": [[2] * 48],
                "eligible": [True],
                "cohort_size": 1,
            }
            for code in ["01", "02"]
        }
        for month, day in [("2024-04", "2024-04-30"), ("2024-05", "2024-05-01")]
    }
    return result, daily


def test_inclusive_cross_month_range_keeps_monthly_models_and_energy():
    result, daily = two_months()
    view = build_range_view(
        result,
        ResultSelection("2024-04", unit="kWh"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    total = next(s for s in view["series"] if s["kind"] == "overall")
    assert total["values"] == [12] * 48 + [36] * 48
    assert len(view["timestamps"]) == 96
    assert view["timestamps"][0] == "2024-04-30T00:00:00"
    assert view["timestamps"][-1] == "2024-05-01T23:30:00"
    assert view["energy_selected_kwh"] == 2304
    assert view["day_count"] == 2
    assert {(f["industry_code"], f["year_month"]) for f in view["factors"]} == {
        (c, m) for c in ["01", "02"] for m in ["2024-04", "2024-05"]
    }


def test_range_normalizes_after_concatenation_and_resampling():
    result, daily = two_months()
    view = build_range_view(
        result,
        ResultSelection(
            "2024-04", unit="kW", normalization="mean", interval_minutes=60
        ),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    assert view["series"][0]["values"] == pytest.approx([0.5] * 24 + [1.5] * 24)
    assert view["unit"] == "p.u."
    assert view["energy_selected_kwh"] == 2304


@pytest.mark.parametrize(
    "start,end",
    [("2024-05-01", "2024-04-30"), ("2024-03-31", "2024-04-01"), ("bad", "2024-04-30")],
)
def test_invalid_ranges_are_rejected(start, end):
    result, daily = two_months()
    with pytest.raises(ValueError):
        build_range_view(
            result,
            ResultSelection("2024-04"),
            daily,
            start,
            end,
            method="representative",
        )


def test_missing_date_does_not_turn_into_zero_or_normalized_partial_shape():
    result, daily = two_months()
    daily["2024-05"].pop("02")
    view = build_range_view(
        result,
        ResultSelection("2024-04"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    assert not view["complete"]
    assert view["series"][0]["values"][48:] == [None] * 48
    normalized = build_range_view(
        result,
        ResultSelection("2024-04", normalization="mean"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    assert normalized["series"][0]["values"] is None


def test_organization_range_unions_industry_scope_and_retains_month_specific_codes():
    result, daily = two_months()
    result["cells"] = [
        c
        for c in result["cells"]
        if not (c["year_month"] == "2024-04" and c["industry_code"] == "02")
    ]
    result["industry_universe"]["2024-04"] = ["01"]
    view = build_range_view(
        result,
        ResultSelection("2024-04", level="organization"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    assert view["industry_codes"] == ["01", "02"]
    assert view["month_scopes"]["2024-04"]["industry_codes"] == ["01"]
    assert view["month_scopes"]["2024-05"]["industry_codes"] == ["01", "02"]
