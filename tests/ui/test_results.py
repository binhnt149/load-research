import copy
import csv
from datetime import datetime, timedelta

import pytest

from load_research.application.models import SourceInput, StudyRequest
from load_research.domain.config import RunConfig, SourceOptions
from load_research.ui.results import ResultsView
from load_research.ui.window import MainWindow
from load_research.workspace import Workspace


def result_data():
    values = [10.0, 20.0] * 24
    return {
        "run_id": "a" * 32,
        "status": "completed",
        "method_version": "class-profile-v1",
        "config": {"interval_minutes": 30, "scope": "NPC", "min_customers": 10},
        "quality": [],
        "calendar": {},
        "sources": [],
        "cells": [
            {
                "industry_code": "01",
                "year_month": "2024-02",
                "billing_basis": "calendar_month",
                "day_counts": {"weekday": 29},
                "result": {
                    "status": "valid",
                    "sample": {"weekday": values},
                    "energy": {"weekday": values},
                    "contributions": {"weekday": {"group_1": values}},
                    "sample_contributions": {"weekday": {"group_1": values}},
                    "alpha": 1,
                    "billing_kwh": 20880,
                    "background_kwh": 20880,
                    "diagnostics": {"cohort_size": 1},
                },
                "clusters": {
                    "weekday": {
                        "diagnostics": {"silhouette": None},
                        "centroids": {},
                        "assignments": {"001": "group_1"},
                    }
                },
                "members": [
                    {
                        "customer_id": "001",
                        "day_type": "weekday",
                        "cluster_id": "group_1",
                        "days_used": 20,
                    }
                ],
            }
        ],
    }


def test_results_filters_show_real_24_48_values_and_dimensionless_shapes(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result_data())
    view.set_resolution(60)
    assert view.table_model.rowCount() == 24
    assert view.table_model.records[0]["Chung"] == 30
    view.set_resolution(30)
    assert view.table_model.rowCount() == 48
    assert view.table_model.records[0]["Chung"] == 20  # 10 kWh / 0.5h
    view.set_normalization("mean")
    assert sum(row["Chung"] for row in view.table_model.records) / 48 == pytest.approx(
        1
    )
    assert "kW" not in view.canvas.figure.axes[0].get_ylabel()
    assert view.export_options(selected=True)["industry_codes"] == ("01",)
    assert view.export_options(selected=False)["industry_codes"] == ()


def test_comparison_explains_configuration_and_cohort_changes(qtbot):
    view = ResultsView()
    qtbot.addWidget(view)
    current, other = result_data(), copy.deepcopy(result_data())
    other["run_id"] = "b" * 32
    other["config"]["min_customers"] = 20
    other["calendar"] = {"holidays": ["2024-02-10"]}
    other["cells"][0]["members"][0]["customer_id"] = "002"
    view.set_result(current)
    view.set_comparison(other)
    assert "min_customers" in view.comparison_label.text()
    assert "calendar" in view.comparison_label.text()
    assert "1" in view.comparison_label.text()
    assert len(view.canvas.figure.axes[0].lines) >= 2


def test_comparison_handles_missing_current_scaled_curve(qtbot):
    current, other = result_data(), result_data()
    current["cells"][0]["result"]["energy"] = {}
    current["cells"][0]["result"]["status"] = "missing_billing"
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(current)
    view.set_comparison(other)
    assert "thiếu" in view.comparison_label.text()


def test_desktop_button_runs_real_pipeline_without_blocking_event_loop(qtbot, tmp_path):
    cmis, mdms, billing = (
        tmp_path / name for name in ("cmis.csv", "mdms.csv", "billing.csv")
    )
    cmis.write_text("customer_id,industry_code,meter_id\n0001,01,M1\n")
    billing.write_text(
        "industry_code,year_month,billing_energy,unit,billing_basis\n01,2024-02,10000,kWh,calendar_month\n"
    )
    with mdms.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["meter_id", "timestamp", "value", "source_quality_flag"])
        start = datetime(2024, 2, 1)
        for index in range(29 * 48):
            writer.writerow(
                ["M1", (start + timedelta(minutes=index * 30)).isoformat(), 1, "actual"]
            )
    config = RunConfig(
        periods=("2024-02",), scope="NPC", min_customers=1, memory_limit_mb=128
    )
    request = StudyRequest(
        config,
        (str(cmis),),
        (SourceInput(str(mdms), SourceOptions(values_already_scaled=True)),),
        (str(billing),),
    )
    workspace = Workspace.create(tmp_path / "project")
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_project(workspace.root)
    window.set_request(request)
    window.start_research()
    assert window.timer.isActive()
    qtbot.waitUntil(
        lambda: window.current_result is not None or window.last_error is not None,
        timeout=30000,
    )
    assert window.last_error is None
    assert window.current_result["cells"][0]["result"]["status"] == "valid"
    assert window.results.table_model.rowCount() == 48
    qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
    window.poll_job()
    window.start_export(
        tmp_path / "ui-report",
        {"include_xlsx": False, **window.results.export_options(selected=True)},
    )
    qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
    window.poll_job()
    assert window.last_error is None
    assert (tmp_path / "ui-report" / "profiles.csv").is_file()
