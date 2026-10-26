import pytest
from test_pipeline import request_files

from load_research.application.pipeline import run_study
from load_research.workspace import Workspace


def test_desktop_loads_and_exports_both_daily_methods_in_workers(qtbot, tmp_path):
    import csv

    from load_research.ui.results import ResultsView
    from load_research.ui.window import MainWindow

    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path))
    window = MainWindow()
    qtbot.addWidget(window)
    window.workspace = workspace
    window.load_run(result["run_id"])
    view: ResultsView = window.results
    view.mode.setCurrentIndex(view.mode.findData("daily"))
    view.request_daily()
    qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
    window.poll_job()
    assert window.last_error is None, window.last_error_details
    assert view.current_view["complete"]
    assert view.table_model.records[0]["Chung"] > 0
    for method in ("representative", "variation"):
        view.daily_method.setCurrentIndex(view.daily_method.findData(method))
        options = {
            **view.export_options(selected=True),
            "include_xlsx": True,
            "layout": "long",
        }
        window.start_export(tmp_path / method, options)
        qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
        window.poll_job()
        assert window.last_error is None
        with (tmp_path / method / "profiles.csv").open(encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        total = [row for row in rows if row["Loại đường biểu diễn"] == "Tổng hợp"]
        assert len(total) == 48
        assert float(total[0]["Giá trị"]) == pytest.approx(
            view.table_model.records[0]["Chung"]
        )
