import copy

import pytest
from matplotlib.backend_bases import MouseEvent
from test_results import result_data

from load_research.ui.results import ResultsView


def test_multiple_industries_and_named_component_keep_total_and_comparisons(qtbot):
    result = result_data()
    second = copy.deepcopy(result["cells"][0])
    second["industry_code"] = "02"
    result["cells"].append(second)
    result["industry_universe"] = {"2024-02": ["01", "02"]}
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    view.industry.set_selected(("01", "02"))
    assert view.table_model.records[0]["Chung"] == 40
    assert len(view.canvas.figure.axes[0].lines) >= 3
    view.level.setCurrentIndex(view.level.findData("component"))
    view.component_name.setText("Sản xuất")
    assert view.current_view["level"] == "component"
    assert view.export_options(selected=True)["industry_codes"] == ("01", "02")
    view.level.setCurrentIndex(view.level.findData("organization"))
    assert view.current_view["complete"]


def test_clicking_chart_displays_period_and_value(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.show()
    view.resize(1100, 820)
    view.canvas.draw()
    axes = view.canvas.figure.axes[0]
    x, y = axes.transData.transform((0, 20))
    event = MouseEvent("button_press_event", view.canvas, x, y, button=1)
    view.canvas.callbacks.process("button_press_event", event)
    assert "00:00" in view.point_label.text()
    assert "20" in view.point_label.text() and "kW" in view.point_label.text()
    view.set_resolution(60)
    assert view.point_label.text() == "Bấm biểu đồ để xem số liệu chu kỳ."


def test_daily_options_offer_both_methods_and_display_loaded_source_and_model(qtbot):
    result = result_data()
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    view.mode.setCurrentIndex(view.mode.findData("daily"))
    assert {
        view.daily_method.itemData(i) for i in range(view.daily_method.count())
    } == {"representative", "variation"}
    view.set_daily_data(
        {
            "01": {
                "dates": ["2024-02-01"],
                "day_types": ["weekday"],
                "source": [[10] * 48],
                "processed": [[20] * 48],
                "cohort_size": 1,
                "eligible": [True],
            }
        }
    )
    assert view.current_view["date"] == "2024-02-01"
    assert view.table_model.records[0]["Chung"] == pytest.approx(20)
    assert any("Mẫu nguồn" in key for key in view.table_model.records[0])


def test_day_type_selection_refreshes_dates_using_saved_calendar(qtbot):
    result = result_data()
    cell = result["cells"][0]
    cell["day_counts"] = {"weekday": 25, "saturday": 4}
    for key in ("sample", "energy", "contributions", "sample_contributions"):
        cell["result"][key]["saturday"] = copy.deepcopy(cell["result"][key]["weekday"])
    result["calendar"] = {
        "overrides": {"2024-02-03": "weekday", "2024-02-05": "saturday"}
    }
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    view.day_type.set_selected(("saturday",))
    assert view.date.currentData() == "2024-02-05"
    assert view.date.findData("2024-02-03") == -1


def test_rejected_mdms_rows_explain_cause_and_source_coordinates_in_vietnamese(qtbot):
    result = result_data()
    result["sources"] = [{"path": "/data/mdms.csv", "sha256": "abc"}]
    result["import"] = {
        "issues_preview": [
            {
                "source_id": "abc",
                "source_row": 8,
                "source_slot": 2,
                "reason": "measurement must be finite and non-negative",
            }
        ]
    }
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    row = view.import_model.records[0]
    assert "mdms.csv" in row["message"] and "dòng 8" in row["message"]
    assert "không âm" in row["message"]
    assert "measurement must" not in row["message"]
