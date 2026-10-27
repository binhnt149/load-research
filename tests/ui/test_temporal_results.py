import pytest
from PySide6.QtCore import QDate
from test_results import result_data

from load_research.customer_view import build_customer_view
from load_research.ui.results import ResultsView


def test_range_controls_emit_inclusive_dates_and_reject_stale_worker_result(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    assert view.mode.findData("range") >= 0
    view.mode.setCurrentIndex(view.mode.findData("range"))
    view.temporal.start.setDate(QDate(2024, 2, 1))
    view.temporal.end.setDate(QDate(2024, 2, 2))
    with qtbot.waitSignal(view.temporal_requested) as signal:
        view.request_daily()
    payload = signal.args[0]
    assert payload["date_start"] == "2024-02-01" and payload["date_end"] == "2024-02-02"
    view.temporal.end.setDate(QDate(2024, 2, 3))
    assert not view.temporal.accept_data(
        {}, {k: v for k, v in payload.items() if k != "token"}, payload["token"]
    )
    assert view.current_view is None


def test_customer_mode_is_searchable_has_two_curves_and_no_group_selector(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.mode.setCurrentIndex(view.mode.findData("customer"))
    assert view.temporal.customer.isEditable()
    view.temporal.customer.setCurrentText("0001")
    view.temporal.start.setDate(QDate(2024, 2, 1))
    view.temporal.end.setDate(QDate(2024, 2, 2))
    with qtbot.waitSignal(view.temporal_requested) as signal:
        view.request_daily()
    payload = signal.args[0]
    assert payload["customer_id"] == "0001"
    assert view.temporal.accept_data(
        build_customer_view(
            {
                "run_id": view.result["run_id"],
                "customer_id": "0001",
                "interval_minutes": 30,
                "organization_scope": "NPC",
                "date_start": "2024-02-01",
                "date_end": "2024-02-02",
                "days": [
                    {
                        "date": d,
                        "day_type": "weekday",
                        "industry_code": "01",
                        "eligible": True,
                    }
                    for d in ["2024-02-01", "2024-02-02"]
                ],
                "rows": [
                    {
                        "date": d,
                        "slot_index": k + 1,
                        "original_kwh": 2,
                        "repaired_kwh": 3,
                    }
                    for d in ["2024-02-01", "2024-02-02"]
                    for k in range(48)
                ],
            }
        ),
        {k: v for k, v in payload.items() if k != "token"},
        payload["token"],
    )
    view.render_results()
    assert len(view.table_model.records) == 96
    assert {s["kind"] for s in view.current_view["series"]} == {"source", "processed"}
    assert len(view.canvas.figure.axes[0].lines) == 2
    options = view.export_options(selected=True)
    assert options["customer_id"] == "0001"
    assert options["date_end"] == "2024-02-02"


def test_range_offers_day_types_from_other_saved_months(qtbot):
    import copy

    result = result_data()
    other = copy.deepcopy(result["cells"][0])
    other["year_month"] = "2024-03"
    other["day_counts"]["holiday"] = 1
    result["cells"].append(other)
    result["config"]["periods"] = ["2024-02", "2024-03"]
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    view.mode.setCurrentIndex(view.mode.findData("range"))
    assert view.day_type.findData("holiday") >= 0


def test_customer_and_range_hide_filters_that_do_not_apply(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.show()
    view.mode.setCurrentIndex(view.mode.findData("range"))
    assert not view.period.isVisible()
    view.mode.setCurrentIndex(view.mode.findData("customer"))
    assert not view.industry.isVisible() and not view.day_type.isVisible()
    assert not view.component_selector.isVisible()


def test_date_fields_follow_light_theme(qtbot):
    from load_research.ui.window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.results.set_result(result_data())
    window.tabs.setCurrentWidget(window.result_host)
    window.results.mode.setCurrentIndex(window.results.mode.findData("range"))
    window.show()
    window.resize(1024, 768)
    qtbot.wait(100)
    for control in (window.results.temporal.start, window.results.temporal.end):
        pixels = control.grab().toImage()
        brightness = [
            sum(pixels.pixelColor(x, y).getRgb()[:3]) / 765
            for x in range(5, pixels.width() - 25)
            for y in range(3, 6)
        ]
        assert sum(brightness) / len(brightness) > 0.7, (
            "Trường ngày tối, chữ không đủ tương phản trên theme sáng"
        )


@pytest.mark.parametrize("open_project", [False, True])
def test_completed_temporal_response_cannot_cross_project_boundary(
    qtbot, tmp_path, open_project
):
    from types import SimpleNamespace

    from load_research.ui.window import MainWindow
    from load_research.workspace import Workspace

    old = Workspace.create(tmp_path / "old")
    new = Workspace.create(tmp_path / "new")
    window = MainWindow()
    qtbot.addWidget(window)
    window.workspace = old
    window.current_result = result_data()
    view = window.results
    view.set_result(window.current_result)
    view.mode.setCurrentIndex(view.mode.findData("range"))
    context = view.temporal.context()
    view.temporal.token = "pending-A"
    batches = iter(
        [
            [
                {
                    "stage": "temporal_loaded",
                    "run_id": window.current_result["run_id"],
                    "context": context,
                    "token": "pending-A",
                    "details": {"marker": "project-A"},
                }
            ],
            [],
        ]
    )
    window.job = SimpleNamespace(
        root=old.root,
        is_running=False,
        process=None,
        poll=lambda: next(batches, []),
        join=lambda _: None,
        close=lambda: None,
    )
    if open_project:
        window.open_project(new.root)
    else:
        window.workspace = new
    window.poll_job()
    assert view.temporal.cached_view is None
    if open_project:
        assert window.current_result is None and view.result is None
    assert view.current_view is None and view.table_model.records == []
