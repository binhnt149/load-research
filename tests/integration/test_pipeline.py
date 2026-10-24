import csv
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from load_research.application.models import SourceInput, StudyRequest
from load_research.application.pipeline import ResearchCancelled, run_study
from load_research.domain.config import RunConfig, SourceOptions
from load_research.workspace import Workspace


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def request_files(tmp_path, *, billing=True):
    cmis, mdms, totals = [
        tmp_path / name for name in ("cmis.csv", "mdms.csv", "billing.csv")
    ]
    write_csv(
        cmis,
        ["customer_id", "industry_code", "meter_id"],
        [["0001", "01", "M1"], ["0002", "01", "M2"]],
    )
    rows = []
    for day in range(29):
        date = datetime(2024, 2, 1) + timedelta(days=day)
        for slot in range(48):
            timestamp = date + timedelta(minutes=slot * 30)
            level = 2 if date.weekday() < 5 else 1
            rows += [
                [meter, timestamp.isoformat(), level * factor]
                for meter, factor in (("M1", 1), ("M2", 2))
            ]
    write_csv(mdms, ["meter_id", "timestamp", "value"], rows)
    write_csv(
        totals,
        ["industry_code", "year_month", "billing_energy", "unit", "billing_basis"],
        [["01", "2024-02", 100000, "kWh", "calendar_month"]],
    )
    config = replace(
        RunConfig(periods=("2024-02",), scope="NPC"),
        min_customers=1,
        memory_limit_mb=128,
    )
    return StudyRequest(
        config,
        (str(cmis),),
        (SourceInput(str(mdms), SourceOptions(values_already_scaled=True)),),
        (str(totals),) if billing else (),
    )


def test_real_file_pipeline_conserves_energy_and_persists_reproducible_run(tmp_path):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    first = run_study(workspace, request)
    second = run_study(workspace, request)
    assert first["run_id"] != second["run_id"]
    assert first["cells"] == second["cells"]
    assert first["cells"][0]["result"]["diagnostics"]["balance_error_kwh"] < 1e-6
    assert (
        workspace.read_run(first["run_id"])["status"] == "completed_with_warnings"
    )  # source quality unknown
    assert (
        workspace.load_artifact(first["run_id"], "result.json")["cells"]
        == first["cells"]
    )
    workspace.verify_sources(first["run_id"])


def test_missing_billing_marks_run_partial_without_fake_scaled_curve(tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path, billing=False))
    assert result["status"] == "partial"
    assert result["cells"][0]["result"]["status"] == "missing_billing"
    assert result["cells"][0]["result"]["energy"] == {}


def test_cancellation_preserves_previously_completed_runs(tmp_path):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    completed = run_study(workspace, request)
    with pytest.raises(ResearchCancelled):
        run_study(workspace, request, cancelled=lambda: True)
    assert workspace.load_artifact(completed["run_id"], "result.json")["cells"]
    assert any(run["status"] == "cancelled" for run in workspace.list_runs())


def test_changed_source_is_rejected_before_cache_or_result_publication(tmp_path):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")

    def change(event):
        if event["stage"] == "started":
            path = tmp_path / "mdms.csv"
            path.write_text(path.read_text().replace(",2\n", ",20\n"))

    with pytest.raises(ValueError, match="source"):
        run_study(workspace, request, on_progress=change)
    assert not list((workspace.root / "cache").glob("*.json"))
    assert not list((workspace.root / "runs").glob("*/artifacts/result.json"))


def test_one_invalid_clustering_cell_does_not_discard_other_industries(tmp_path):
    request = request_files(tmp_path)
    cmis = tmp_path / "cmis.csv"
    cmis.write_text(cmis.read_text().replace("0002,01", "0002,02"))
    with (tmp_path / "billing.csv").open("a") as stream:
        stream.write("02,2024-02,1000,kWh,calendar_month\n")
    # Industry 01 cannot support two shapes; 02 has inactive curves, which require no KMeans.
    mdms = tmp_path / "mdms.csv"
    import re

    mdms.write_text(re.sub(r"(M2,[^,]+),[^\n]+", r"\1,0", mdms.read_text()))
    request = replace(request, config=replace(request.config, manual_k=2))
    result = run_study(Workspace.create(tmp_path / "project"), request)
    assert result["status"] == "partial"
    cells = {cell["industry_code"]: cell for cell in result["cells"]}
    assert cells["01"]["result"]["status"] == "needs_review"
    assert cells["02"]["result"]["status"] != "needs_review"
    assert cells["01"]["error"]["code"] == "CELL_METHOD_ERROR"


def test_sample_cmis_reconciliation_requires_confirmed_calendar_basis(tmp_path):
    request = request_files(tmp_path)
    cmis = tmp_path / "cmis.csv"
    cmis.write_text(
        "customer_id,industry_code,meter_id,year_month,sample_billing_kwh,sample_billing_basis\n"
        "0001,01,M1,2024-02,2400,calendar_month\n0002,01,M2,2024-02,4800,billing_label_month\n"
    )
    result = run_study(Workspace.create(tmp_path / "project"), request)
    comparison = result["quality"][0]["cmis_reconciliation"]
    assert comparison["status"] == "available"
    assert comparison["customers"]["0001"]["cmis_kwh"] == 2400
    assert comparison["customers"]["0001"]["mdms_original_kwh"] == 2400
    assert comparison["customers"]["0002"]["status"] == "N/A"
