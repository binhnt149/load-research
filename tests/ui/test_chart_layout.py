"""Chart geometry must follow the visible Qt canvas after every filter change."""

import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QFontDatabase, QFontMetrics
from PySide6.QtWidgets import QCheckBox, QComboBox, QPushButton
from test_results import result_data

from load_research.ui.window import MainWindow


def test_gui_checks_have_real_fonts_instead_of_box_fallback(qapp):
    assert QFontDatabase.families(), "Qt did not discover any fonts"
    metrics = QFontMetrics(
        QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    )
    assert metrics.horizontalAdvance("iii") < metrics.horizontalAdvance("WWW")


def layout_sizes(widget):
    layout = widget.layout()
    if layout is None:
        return {}
    rows = []
    for index in range(layout.count()):
        item = layout.itemAt(index)
        children = []
        child_layout = item.layout()
        if child_layout is not None:
            for number in range(child_layout.count()):
                child = child_layout.itemAt(number).widget()
                if child is not None:
                    children.append(
                        (type(child).__name__, child.minimumSizeHint().toTuple())
                    )
        rows.append((index, item.minimumSize().toTuple(), children))
    return {
        "widget": type(widget).__name__,
        "hint": widget.minimumSizeHint().toTuple(),
        "rows": rows,
    }


def assert_chart_and_controls_fit(window):
    view = window.results
    canvas = view.canvas
    canvas.draw()
    renderer = canvas.get_renderer()
    width = canvas.width() * canvas.device_pixel_ratio
    height = canvas.height() * canvas.device_pixel_ratio
    axes = canvas.figure.axes[0]
    bounds = [axes.get_tightbbox(renderer)]
    bounds.extend(
        text.get_window_extent(renderer)
        for text in canvas.figure.texts
        if text.get_visible() and text.get_text()
    )
    for bounds_item in bounds:
        assert bounds_item.x0 >= -1
        assert bounds_item.y0 >= -1
        assert bounds_item.x1 <= width + 1, (
            f"Chart labels extend past canvas width: {bounds_item.bounds}; "
            f"visible canvas {width}×{height}"
        )
        assert bounds_item.y1 <= height + 1, (
            f"Chart labels extend past canvas height: {bounds_item.bounds}; "
            f"visible canvas {width}×{height}"
        )
    for widget_type in (QComboBox, QCheckBox, QPushButton):
        for widget in view.findChildren(widget_type):
            if widget.isVisible():
                bounds_in_window = QRect(
                    widget.mapTo(window, QPoint(0, 0)), widget.size()
                )
                assert window.rect().contains(bounds_in_window)


@pytest.mark.parametrize("size", [(1024, 768), (1240, 860)])
def test_result_chart_labels_and_controls_fit_after_resize_and_option_changes(
    qtbot, size
):
    window = MainWindow()
    qtbot.addWidget(window)
    window.results.set_result(result_data())
    window.tabs.setCurrentWidget(window.result_host)
    window.show()
    window.resize(*size)
    if window.minimumSizeHint().width() > size[0]:
        import json

        print(
            json.dumps(
                [
                    layout_sizes(widget)
                    for widget in (
                        window.centralWidget(),
                        window.result_host,
                        window.results,
                    )
                ],
                indent=2,
            )
        )
    assert window.minimumSizeHint().width() <= size[0], (
        window.minimumSizeHint().toTuple()
    )
    assert window.minimumSizeHint().height() <= size[1], (
        window.minimumSizeHint().toTuple()
    )
    qtbot.waitUntil(lambda: window.size().toTuple() == size)
    qtbot.wait(1)
    assert_chart_and_controls_fit(window)

    # A new figure must use the current viewport even if Qt emits no resize event.
    window.results.unit.setCurrentIndex(1)
    qtbot.wait(1)
    assert_chart_and_controls_fit(window)
    window.results.set_normalization("mean")
    qtbot.wait(1)
    assert_chart_and_controls_fit(window)

    window.resize(1366, 900)
    qtbot.waitUntil(lambda: window.size().toTuple() == (1366, 900))
    qtbot.wait(1)
    assert_chart_and_controls_fit(window)
    window.resize(1024, 768)
    qtbot.waitUntil(lambda: window.size().toTuple() == (1024, 768))
    qtbot.wait(1)
    window.results.set_resolution(60)
    qtbot.wait(1)
    assert_chart_and_controls_fit(window)


def test_daily_chart_with_point_values_fits_small_window(qtbot):
    import copy

    from matplotlib.backend_bases import MouseEvent

    result = result_data()
    other = copy.deepcopy(result["cells"][0])
    other["industry_code"] = "02"
    result["cells"].append(other)
    window = MainWindow()
    qtbot.addWidget(window)
    view = window.results
    view.set_result(result)
    view.industry.set_selected(("01", "02"))
    window.tabs.setCurrentWidget(window.result_host)
    window.show()
    window.resize(1024, 768)
    view.mode.setCurrentIndex(view.mode.findData("daily"))
    view.set_daily_data(
        {
            code: {
                "dates": ["2024-02-01"],
                "day_types": ["weekday"],
                "source": [[10] * 48],
                "processed": [[20] * 48],
                "eligible": [True],
                "cohort_size": 1,
            }
            for code in ("01", "02")
        }
    )
    view.canvas.draw()
    axes = view.canvas.figure.axes[0]
    x, y = axes.transData.transform((0, 40))
    view.canvas.callbacks.process(
        "button_press_event",
        MouseEvent("button_press_event", view.canvas, x, y, button=1),
    )
    qtbot.waitUntil(lambda: window.size().toTuple() == (1024, 768))
    assert_chart_and_controls_fit(window)


def test_many_industry_selection_keeps_summary_and_chart_within_window(qtbot):
    import copy

    result = result_data()
    template = result["cells"][0]
    result["cells"] = [
        {**copy.deepcopy(template), "industry_code": f"{index:02}"}
        for index in range(50)
    ]
    window = MainWindow()
    qtbot.addWidget(window)
    window.results.set_result(result)
    window.results.industry.set_selected(tuple(f"{index:02}" for index in range(50)))
    window.tabs.setCurrentWidget(window.result_host)
    window.show()
    window.resize(1024, 768)
    qtbot.waitUntil(lambda: window.size().toTuple() == (1024, 768))
    assert_chart_and_controls_fit(window)
