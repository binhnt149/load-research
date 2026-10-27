import pytest

from load_research.customer_view import build_customer_view, convert_temporal_view
from load_research.result_view import ResultSelection


def details():
    return {
        "run_id": "r",
        "customer_id": "0001",
        "interval_minutes": 30,
        "organization_scope": "NPC",
        "date_start": "2024-02-01",
        "date_end": "2024-02-02",
        "days": [
            {"date": d, "day_type": "weekday", "industry_code": "01", "eligible": True}
            for d in ["2024-02-01", "2024-02-02"]
        ],
        "rows": [
            {
                "date": d,
                "slot_index": slot + 1,
                "original_kwh": level,
                "repaired_kwh": level,
            }
            for d, level in [("2024-02-01", 2), ("2024-02-02", 6)]
            for slot in range(48)
        ],
    }


def test_customer_view_keeps_two_series_and_converts_without_weights_or_expansion():
    view = build_customer_view(details())
    assert {r["kind"] for r in view["series"]} == {"source", "processed"}
    assert view["customer_id"] == "0001"
    assert view["energy_selected_kwh"] == 384
    converted = convert_temporal_view(
        view, ResultSelection("2024-02", interval_minutes=60, unit="kW")
    )
    assert converted["series"][1]["values"] == [4] * 24 + [12] * 24
    assert len(converted["timestamps"]) == 48
    normalized = convert_temporal_view(
        view, ResultSelection("2024-02", interval_minutes=60, normalization="mean")
    )
    assert normalized["series"][1]["values"] == pytest.approx([0.5] * 24 + [1.5] * 24)


def test_customer_gap_propagates_in_hourly_conversion_without_hiding_other_days():
    data = details()
    data["rows"][0]["original_kwh"] = None
    view = convert_temporal_view(
        build_customer_view(data),
        ResultSelection("2024-02", interval_minutes=60, unit="kWh"),
    )
    assert view["series"][0]["values"][0] is None
    assert view["series"][0]["values"][1] == 4
    assert view["series"][1]["values"][0] == 4
