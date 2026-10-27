"""Date-range/customer controls share the chart viewport on small windows."""

import pytest
from PySide6.QtCore import QDate, QPoint, QRect, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
)
from test_chart_layout import assert_chart_and_controls_fit
from test_results import result_data

from load_research.customer_view import build_customer_view
from load_research.result_range import build_range_view
from load_research.result_view import ResultSelection
from load_research.ui.window import MainWindow

DATES = ["2024-02-01", "2024-02-02"]


def _canonical_view(result, mode):
    if mode == "customer":
        return build_customer_view(
            {
                "run_id": result["run_id"],
                "customer_id": "001",
                "interval_minutes": 30,
                "organization_scope": "NPC",
                "date_start": DATES[0],
                "date_end": DATES[-1],
                "days": [
                    {
                        "date": day,
                        "day_type": "weekday",
                        "industry_code": "01",
                        "eligible": True,
                    }
                    for day in DATES
                ],
                "rows": [
                    {
                        "date": day,
                        "slot_index": slot + 1,
                        "original_kwh": 2,
                        "repaired_kwh": 3,
                        "quality_known": True,
                        "estimated": False,
                    }
                    for day in DATES
                    for slot in range(48)
                ],
            }
        )
    daily = {
        "01": {
            "dates": DATES,
            "day_types": ["weekday", "weekday"],
            "source": [[2] * 48, [4] * 48],
            "processed": [[3] * 48, [6] * 48],
            "eligible": [True, True],
            "cohort_size": 1,
        }
    }
    return build_range_view(
        result,
        ResultSelection("2024-02", ("01",), ("weekday",), unit="kWh"),
        {"2024-02": daily},
        DATES[0],
        DATES[-1],
        method="representative",
    )


def _assert_temporal_layout_fits(window, size):
    view = window.results
    view.summary.setText(
        "Phụ tải của hai ngày đã chọn · kiểm tra chất lượng dữ liệu\n"
        "Điện năng sau VEE và trạng thái tổng hợp được giữ để đối chiếu."
    )
    view.point_label.setText(
        "2024-02-01 00:00 · Phụ tải sau VEE: 6 kW\nPhụ tải trước VEE: 4 kW · Chu kỳ 1"
    )
    window.layout().activate()
    window.centralWidget().layout().activate()
    view.layout().activate()
    assert window.minimumSizeHint().width() <= size[0], (
        f"{view.mode.currentData()} controls require a wider window: "
        f"{window.minimumSizeHint().toTuple()}"
    )
    assert window.minimumSizeHint().height() <= size[1], (
        f"{view.mode.currentData()} controls require a taller window: "
        f"{window.minimumSizeHint().toTuple()}"
    )
    assert window.size().toTuple() == size
    assert_chart_and_controls_fit(window)
    for label in (view.summary, view.point_label):
        required = label.fontMetrics().boundingRect(
            label.contentsRect(), Qt.TextFlag.TextWordWrap, label.text()
        )
        assert required.height() <= label.contentsRect().height(), (
            f"Two-line label is clipped: needs {required.height()}, "
            f"has {label.contentsRect().height()}"
        )
    for widget_type in (
        QDateEdit,
        QLineEdit,
        QComboBox,
        QCheckBox,
        QPushButton,
        QToolButton,
        QLabel,
    ):
        for widget in view.findChildren(widget_type):
            if not widget.isVisible():
                continue
            ancestor = widget.parentWidget()
            while ancestor is not None:
                bounds = QRect(widget.mapTo(ancestor, QPoint(0, 0)), widget.size())
                assert ancestor.rect().contains(bounds), (
                    f"{type(widget).__name__} {widget.accessibleName()!r} is clipped "
                    f"by {type(ancestor).__name__}: {bounds.getRect()} "
                    f"outside {ancestor.rect().getRect()}"
                )
                if ancestor is window:
                    break
                ancestor = ancestor.parentWidget()


@pytest.mark.parametrize("size", [(1024, 768), (1240, 860)])
@pytest.mark.parametrize("mode", ["range", "customer"])
def test_temporal_controls_chart_and_two_line_labels_fit_after_option_changes(
    qtbot, size, mode
):
    result = result_data()
    window = MainWindow()
    qtbot.addWidget(window)
    view = window.results
    view.set_result(result)
    window.tabs.setCurrentWidget(window.result_host)
    view.mode.setCurrentIndex(view.mode.findData(mode))
    view.temporal.start.setDate(QDate(2024, 2, 1))
    view.temporal.end.setDate(QDate(2024, 2, 2))
    if mode == "customer":
        assert view.temporal.customer.isEditable()
        view.temporal.customer.setEditText("001")
    token = "layout-regression"
    view.temporal.token = token
    assert view.temporal.accept_data(
        _canonical_view(result, mode), view.temporal.context(), token
    )
    view.render_results()
    assert view.current_view is not None
    assert len(view.table_model.records) == 96
    window.resize(*size)
    window.show()
    qtbot.wait(1)
    assert view.temporal.start.isVisible() and view.temporal.end.isVisible()
    if mode == "customer":
        assert view.temporal.customer.lineEdit().isVisible()
    _assert_temporal_layout_fits(window, size)

    view.unit.setCurrentIndex(view.unit.findData("kWh"))
    qtbot.wait(1)
    _assert_temporal_layout_fits(window, size)
    view.set_resolution(60)
    qtbot.wait(1)
    assert view.current_view is not None
    assert len(view.table_model.records) == 48
    _assert_temporal_layout_fits(window, size)
