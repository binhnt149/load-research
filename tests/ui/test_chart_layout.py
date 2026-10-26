"""Chart geometry must follow the visible Qt canvas after every filter change."""

import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QCheckBox, QComboBox, QPushButton
from test_results import result_data

from load_research.ui.window import MainWindow


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
