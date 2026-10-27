"""Visible series determine the chart range and point feedback, independently."""

import copy

import numpy as np
import pytest
from matplotlib.backend_bases import MouseEvent
from PySide6.QtWidgets import QToolButton
from test_results import result_data

from load_research.result_reporting import render_view
from load_research.result_view import ResultSelection, build_result_view
from load_research.ui.results import ResultsView


def _series_actions(view):
    button = view.findChild(QToolButton, "seriesVisibility")
    assert button is not None, "Cần điều khiển chọn riêng từng đường dữ liệu bằng tên"
    assert button.menu() is not None
    actions = [action for action in button.menu().actions() if action.isCheckable()]
    assert actions, "Danh sách đường dữ liệu cần có lựa chọn bật/tắt"
    return {action.data(): action for action in actions}


def _visible_lines(view):
    return [line for line in view.canvas.figure.axes[0].lines if line.get_visible()]


@pytest.mark.parametrize(
    "pattern",
    [
        pytest.param([100, 110], id="positive-range"),
        pytest.param([-110, -100], id="negative-range"),
        pytest.param([100, None, 110], id="gaps"),
        pytest.param([100], id="constant"),
        pytest.param([0], id="zero"),
        pytest.param([None], id="missing"),
    ],
)
def test_chart_y_range_fits_available_values_without_forcing_zero(pattern):
    report = build_result_view(
        result_data(), ResultSelection("2024-02", ("01",), ("weekday",))
    )
    values = (pattern * 48)[:48]
    report["series"] = [
        {"id": "test-curve", "kind": "overall", "label": "Phụ tải", "values": values}
    ]
    axes = render_view(report).axes[0]
    lower, upper = axes.get_ylim()
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]

    assert np.isfinite([lower, upper]).all()
    assert lower < upper
    if finite.size:
        assert lower < finite.min(), "Điểm thấp nhất cần nằm trong vùng hiển thị"
        assert upper > finite.max(), "Điểm cao nhất cần nằm trong vùng hiển thị"
        if finite.min() > 0:
            assert lower > 0, "Không ép trục Y về 0 khi phụ tải cách xa 0"
        if finite.max() < 0:
            assert upper < 0, "Trục Y cần bám dải âm thay vì cắt tại 0"


def test_named_series_toggle_updates_y_range_without_changing_interval_table(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.mode.setCurrentIndex(view.mode.findData("daily"))
    view.set_daily_data(
        {
            "01": {
                "dates": ["2024-02-01"],
                "day_types": ["weekday"],
                "source": [[1000] * 48],
                "processed": [[20] * 48],
                "cohort_size": 1,
                "eligible": [True],
            }
        }
    )
    source_curve = next(
        row for row in view.current_view["series"] if row["kind"] == "source"
    )
    actions = _series_actions(view)
    action = actions[source_curve["id"]]
    assert action.text() == source_curve["label"]
    assert action.isChecked()
    before = copy.deepcopy(view.table_model.records)
    assert view.canvas.figure.axes[0].get_ylim()[1] > max(source_curve["values"])

    action.trigger()

    assert not action.isChecked()
    assert all(
        line.get_label() != source_curve["label"] for line in _visible_lines(view)
    )
    assert view.canvas.figure.axes[0].get_ylim()[1] < min(source_curve["values"])
    assert view.table_model.records == before
    action.trigger()
    assert action.isChecked()
    assert any(
        line.get_label() == source_curve["label"] for line in _visible_lines(view)
    )
    assert view.canvas.figure.axes[0].get_ylim()[1] > max(source_curve["values"])


def test_chart_point_feedback_omits_hidden_series(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.resize(1100, 820)
    view.show()
    axes = view.canvas.figure.axes[0]
    hidden = next(line for line in axes.lines if "group_1" in line.get_label())
    hidden.set_visible(False)
    view.canvas.draw()
    lower, upper = axes.get_ylim()
    x, y = axes.transData.transform((1, (lower + upper) / 2))
    event = MouseEvent("button_press_event", view.canvas, x, y, button=1)
    assert event.inaxes is axes
    view.canvas.callbacks.process("button_press_event", event)

    assert "Chu kỳ" in view.point_label.text()
    assert "Chung" in view.point_label.text()
    assert hidden.get_label() not in view.point_label.text()


def test_filter_change_resets_visibility_even_if_overall_series_id_is_reused(qtbot):
    result = result_data()
    second = copy.deepcopy(result["cells"][0])
    second["industry_code"] = "02"
    result["cells"].append(second)
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    overall = next(
        row for row in view.current_view["series"] if row["kind"] == "overall"
    )
    action = _series_actions(view)[overall["id"]]
    action.trigger()
    assert not action.isChecked()
    assert all(line.get_label() != "Chung" for line in _visible_lines(view))

    view.industry.set_selected(("02",))

    new_overall = next(
        row for row in view.current_view["series"] if row["kind"] == "overall"
    )
    assert new_overall["id"] == overall["id"]
    assert _series_actions(view)[new_overall["id"]].isChecked()
    assert any(line.get_label() == "Chung" for line in _visible_lines(view))


def test_hiding_series_clears_old_point_tooltip(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.point_label.setToolTip("Giá trị điểm cũ")
    view.series_visibility.set_all(False)
    assert view.point_label.toolTip() == ""


def test_series_menu_is_cleared_when_daily_data_has_not_loaded(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    assert view.series_visibility.isEnabled()
    view.mode.setCurrentIndex(view.mode.findData("daily"))
    assert view.current_view is None
    assert not view.series_visibility.isEnabled()
    assert not [a for a in view.series_visibility.menu().actions() if a.isCheckable()]


@pytest.mark.parametrize("hide_overall", [False, True])
def test_hidden_stacked_series_has_identical_geometry_in_export(qtbot, hide_overall):
    view = ResultsView()
    qtbot.addWidget(view)
    report = build_result_view(result_data(), ResultSelection("2024-02"))
    report["series"] = [
        {"id": "overall", "kind": "overall", "label": "Chung", "values": [5] * 48},
        {"id": "a", "kind": "behavior", "label": "A", "values": [2] * 48},
        {"id": "b", "kind": "behavior", "label": "B", "values": [3] * 48},
    ]
    render_view(report, figure=view.canvas.figure, stacked=True)
    view.series_visibility.reset()
    _series_actions(view)["a"].trigger()
    if hide_overall:
        _series_actions(view)["overall"].trigger()
    screen = next(
        a for a in view.canvas.figure.axes[0].collections if a.get_gid() == "b"
    )
    exported = render_view(
        {**report, "hidden_series_ids": view.series_visibility.hidden_ids()},
        stacked=True,
    ).axes[0]
    image = next(a for a in exported.collections if a.get_gid() == "b")
    np.testing.assert_array_equal(
        screen.get_paths()[0].vertices, image.get_paths()[0].vertices
    )
    assert exported.get_legend() is not None
    assert "A" not in [text.get_text() for text in exported.get_legend().get_texts()]
    assert not any(a.get_visible() and a.get_gid() == "a" for a in exported.collections)
