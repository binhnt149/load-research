import csv
from dataclasses import asdict

import pytest
from PySide6.QtCore import QDate
from test_pipeline import request_files

from load_research.application.pipeline import ResearchCancelled, run_study
from load_research.application.temporal import load_temporal_view
from load_research.result_view import ResultSelection
from load_research.ui.window import MainWindow
from load_research.workspace import Workspace


def test_short_variation_range_uses_full_month_factor_and_cancels_without_writes(
    tmp_path,
):
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path))
    payload = {
        "run_id": result["run_id"],
        "date_start": "2024-02-01",
        "date_end": "2024-02-02",
        "method": "variation",
        "selection": asdict(ResultSelection("2024-02", unit="kWh")),
    }
    short = load_temporal_view(workspace, payload)
    full = load_temporal_view(workspace, {**payload, "date_end": "2024-02-29"})
    # 21 weekdays at 288 kWh and 8 weekend days at 144 kWh: 7,200 kWh/month.
    assert short["daily_factors"][0]["factor"] == pytest.approx(100000 / 7200)
    assert full["daily_factors"][0]["factor"] == short["daily_factors"][0]["factor"]
    assert short["energy_selected_kwh"] == pytest.approx(8000)
    assert full["energy_selected_kwh"] == pytest.approx(100000)

    def cancel():
        raise ResearchCancelled()

    with pytest.raises(ResearchCancelled):
        load_temporal_view(workspace, payload, check=cancel)
    assert workspace.load_artifact(result["run_id"], "result.json") == result


def test_range_and_customer_workers_export_exact_selected_dates(qtbot, tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path))
    window = MainWindow()
    qtbot.addWidget(window)
    window.workspace = workspace
    window.load_run(result["run_id"])
    view = window.results
    for mode in ("range", "customer"):
        view.mode.setCurrentIndex(view.mode.findData(mode))
        view.temporal.start.setDate(QDate(2024, 2, 1))
        view.temporal.end.setDate(QDate(2024, 2, 2))
        if mode == "customer":
            view.temporal.customer.setCurrentText("0001")
        view.request_daily()
        qtbot.waitUntil(
            lambda: window.job is not None and not window.job.is_running, timeout=30000
        )
        window.poll_job()
        assert window.last_error is None, window.last_error_details
        assert len(view.table_model.records) == 96
        options = {
            **view.export_options(selected=True),
            "include_xlsx": True,
            "layout": "long",
            "chart_formats": ("png",),
        }
        window.start_export(tmp_path / mode, options)
        qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
        window.poll_job()
        assert window.last_error is None, window.last_error_details
        with (tmp_path / mode / "profiles.csv").open(encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        assert {row["Ngày"] for row in rows} == {"2024-02-01", "2024-02-02"}
        assert {row["Đơn vị"] for row in rows} == {"kW"}
        if mode == "customer":
            assert {row["Mã khách hàng"] for row in rows} == {"0001"}
            assert (tmp_path / mode / "customer-vee.csv").is_file()
