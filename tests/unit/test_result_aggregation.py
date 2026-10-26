import copy

import numpy as np
import pytest

from load_research.result_view import ResultSelection, build_result_view


def study():
    cells = []
    for code, level, alpha in (("01", 2, 2), ("02", 10, 5)):
        energy = {"weekday": [level] * 48, "saturday": [level * 2] * 48}
        sample = {kind: [v / alpha for v in values] for kind, values in energy.items()}
        billing = 20 * sum(energy["weekday"]) + 10 * sum(energy["saturday"])
        cells.append(
            {
                "industry_code": code,
                "industry_name": "Ngành " + code,
                "year_month": "2024-04",
                "billing_basis": "calendar_month",
                "day_counts": {
                    "weekday": 20,
                    "saturday": 10,
                    "sunday": 0,
                    "holiday": 0,
                },
                "members": [],
                "clusters": {},
                "result": {
                    "status": "valid",
                    "alpha": alpha,
                    "billing_kwh": billing,
                    "background_kwh": billing / alpha,
                    "diagnostics": {"cohort_size": 10},
                    "energy": energy,
                    "sample": sample,
                    "contributions": {
                        kind: {"group_1": values} for kind, values in energy.items()
                    },
                    "sample_contributions": {
                        kind: {"group_1": values} for kind, values in sample.items()
                    },
                },
            }
        )
    return {
        "run_id": "r",
        "config": {"scope": "NPC", "interval_minutes": 30},
        "cells": cells,
        "industry_universe": {"2024-04": ["01", "02"]},
    }


def total(view):
    return next(curve for curve in view["series"] if curve["kind"] == "overall")


def test_industries_are_summed_then_day_types_are_calendar_weighted():
    result = study()
    view = build_result_view(result, ResultSelection("2024-04", ("01", "02")))
    assert view["complete"] and view["day_count"] == 30
    assert total(view)["values"] == pytest.approx([32] * 48)  # 16 kWh / 0.5 h
    assert view["energy_selected_kwh"] == pytest.approx(23040)
    assert view["billing_kwh"] == pytest.approx(23040)
    assert {row["industry_code"]: row["alpha"] for row in view["factors"]} == {
        "01": 2,
        "02": 5,
    }
    assert "alpha" not in total(view)  # no invented common factor after summation


def test_selected_days_have_their_own_energy_total_not_full_month_billing():
    view = build_result_view(
        study(), ResultSelection("2024-04", ("01", "02"), ("saturday",), unit="kWh")
    )
    assert total(view)["values"] == pytest.approx([24] * 48)
    assert view["day_count"] == 10
    assert view["energy_selected_kwh"] == pytest.approx(11520)
    assert view["billing_kwh"] == pytest.approx(23040)


def test_industry_comparisons_and_qualified_behavior_contributions_add_to_total():
    view = build_result_view(study(), ResultSelection("2024-04", ("01", "02")))
    for family in ("industry", "behavior"):
        curves = [curve for curve in view["series"] if curve["kind"] == family]
        assert np.sum([curve["values"] for curve in curves], axis=0) == pytest.approx(
            total(view)["values"]
        )
    behaviors = [curve for curve in view["series"] if curve["kind"] == "behavior"]
    assert len({curve["id"] for curve in behaviors}) == 4
    assert {curve["industry_code"] for curve in behaviors} == {"01", "02"}


def test_day_type_comparisons_are_unweighted_profiles_with_explicit_calendar_weights():
    view = build_result_view(study(), ResultSelection("2024-04", ("01", "02")))
    curves = {
        curve["day_type"]: curve
        for curve in view["series"]
        if curve["kind"] == "day_type"
    }
    assert curves["weekday"]["values"] == pytest.approx([24] * 48)
    assert curves["saturday"]["values"] == pytest.approx([48] * 48)
    assert curves["weekday"]["day_count"] == 20


def test_normalized_total_uses_the_selected_physical_scope_before_normalizing():
    result = study()
    for cell, vector in zip(
        result["cells"], ([0] * 24 + [2] * 24, [10] * 24 + [0] * 24), strict=True
    ):
        for kind in cell["result"]["energy"]:
            cell["result"]["energy"][kind] = vector
            cell["result"]["sample"][kind] = [
                v / cell["result"]["alpha"] for v in vector
            ]
            cell["result"]["contributions"][kind] = {"group_1": vector}
            cell["result"]["sample_contributions"][kind] = {
                "group_1": cell["result"]["sample"][kind]
            }
    selection = ResultSelection("2024-04", ("01", "02"), normalization="mean")
    vector = total(build_result_view(result, selection))["values"]
    assert vector == pytest.approx([5 / 3] * 24 + [1 / 3] * 24)


def test_resolution_change_preserves_daily_and_selected_month_energy():
    result = study()
    view = build_result_view(
        result,
        ResultSelection("2024-04", ("01", "02"), interval_minutes=60, unit="kWh"),
    )
    assert len(total(view)["values"]) == 24
    assert total(view)["values"] == pytest.approx([32] * 24)
    assert view["energy_selected_kwh"] == pytest.approx(23040)


def test_missing_industry_curve_never_becomes_a_zero_or_a_complete_total():
    result = study()
    result["cells"][1]["result"]["energy"] = {}
    result["cells"][1]["result"]["status"] = "missing_billing"
    view = build_result_view(result, ResultSelection("2024-04", ("01", "02")))
    assert not view["complete"] and total(view)["values"] is None
    assert {row["industry_code"] for row in view["missing"]} == {"02"}
    available = [
        c for c in view["series"] if c["kind"] == "industry" and c["values"] is not None
    ]
    assert [c["industry_code"] for c in available] == ["01"]


def test_whole_organization_checks_industry_universe_instead_of_only_visible_cells():
    result = study()
    result["industry_universe"]["2024-04"].append("03")
    view = build_result_view(result, ResultSelection("2024-04", level="organization"))
    assert view["industry_codes"] == ["01", "02", "03"]
    assert not view["complete"] and total(view)["values"] is None
    assert any(row["industry_code"] == "03" for row in view["missing"])


def test_duplicate_selections_are_counted_once_and_input_is_immutable():
    result = study()
    before = copy.deepcopy(result)
    selection = ResultSelection(
        "2024-04",
        ("02", "01", "01"),
        ("weekday", "weekday"),
        level="component",
        name="Sản xuất",
    )
    view = build_result_view(result, selection)
    assert view["industry_codes"] == ["01", "02"]
    assert total(view)["values"] == pytest.approx([24] * 48)
    assert total(view)["label"] == "Sản xuất"
    assert result == before


def test_inconsistent_calendars_are_rejected_before_combining():
    result = study()
    result["cells"][1]["day_counts"]["saturday"] = 9
    with pytest.raises(ValueError, match="calendar"):
        build_result_view(result, ResultSelection("2024-04", ("01", "02")))


def test_zero_consumption_is_physical_zero_and_has_no_normalized_shape():
    result = study()
    for cell in result["cells"]:
        for kind in cell["result"]["energy"]:
            cell["result"]["energy"][kind] = [0] * 48
            cell["result"]["contributions"][kind] = {"inactive": [0] * 48}
    physical = build_result_view(result, ResultSelection("2024-04", ("01", "02")))
    assert total(physical)["values"] == [0] * 48
    normalized = build_result_view(
        result, ResultSelection("2024-04", ("01", "02"), normalization="share")
    )
    assert total(normalized)["values"] is None
