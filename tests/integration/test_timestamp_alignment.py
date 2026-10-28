import csv
import json
from dataclasses import asdict, replace

import pytest
from test_pipeline import request_files

from load_research.application.inspection import inspect_customer
from load_research.application.pipeline import run_study
from load_research.application.result_export import export_selection
from load_research.infrastructure.store import IntervalStore
from load_research.result_view import ResultSelection
from load_research.workspace import Workspace


def test_offset_timestamp_is_imported_and_original_is_auditable(tmp_path):
    request = request_files(tmp_path)
    source = tmp_path / "mdms.csv"
    source.write_text(
        source.read_text().replace(
            "M1,2024-02-01T01:00:00,2\n", "M1,2024-02-01T01:02:02,2\n"
        )
    )
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    assert result["import"]["timestamp_adjustments"] == 1
    detail = inspect_customer(
        workspace, result["run_id"], "0001", "2024-02-01", "2024-02-01"
    )
    assert detail["rows"][2]["original_kwh"] == 2
    database = workspace.safe_path(f"cache/{result['import']['key']}.duckdb")
    with IntervalStore(database, read_only=True) as store:
        corrections = list(store.iter_timestamp_adjustments())
    assert len(corrections) == 1
    assert corrections[0]["original_timestamp"] == "2024-02-01T01:02:02"
    assert corrections[0]["aligned_timestamp"] == "2024-02-01T01:00:00"
    assert corrections[0]["offset_seconds"] == 122

    second = run_study(workspace, request)
    assert second["import"]["key"] == result["import"]["key"]
    assert second["import"]["timestamp_adjustments"] == 1


def test_floor_collision_with_different_measurements_is_rejected(tmp_path):
    request = request_files(tmp_path)
    with (tmp_path / "mdms.csv").open("a") as stream:
        stream.write("M1,2024-02-01T01:25:00,50\n")
    workspace = Workspace.create(tmp_path / "project")
    with pytest.raises(ValueError, match="conflicting duplicate"):
        run_study(workspace, request)


def test_secondary_interval_boundary_adjustment_is_audited(tmp_path):
    request = request_files(tmp_path)
    source = tmp_path / "mdms.csv"
    with source.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    rows[2]["interval_end"] = "2024-02-01T01:02:02"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["meter_id", "timestamp", "value", "interval_end"]
        )
        writer.writeheader()
        writer.writerows(rows)
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    assert result["import"]["timestamp_adjustments"] == 1
    database = workspace.safe_path(f"cache/{result['import']['key']}.duckdb")
    with IntervalStore(database, read_only=True) as store:
        correction = next(store.iter_timestamp_adjustments())
    assert correction["original_interval_end"] == "2024-02-01T01:02:02"
    assert correction["original_timestamp"] == "2024-02-01T00:30:00"


def test_old_source_snapshot_keeps_strict_rejection(tmp_path):
    request = request_files(tmp_path)
    options = replace(request.mdms_sources[0].options, timestamp_alignment="strict")
    request = replace(
        request, mdms_sources=(replace(request.mdms_sources[0], options=options),)
    )
    source = tmp_path / "mdms.csv"
    source.write_text(
        source.read_text().replace(
            "M1,2024-02-01T01:00:00,2\n", "M1,2024-02-01T01:02:02,2\n"
        )
    )
    result = run_study(Workspace.create(tmp_path / "project"), request)
    assert result["import"]["issues_count"] == 1
    assert result["import"]["timestamp_adjustments"] == 0


def test_optional_export_contains_complete_timestamp_audit_and_manifest(tmp_path):
    request = request_files(tmp_path)
    source = tmp_path / "mdms.csv"
    source.write_text(
        source.read_text().replace(
            "M1,2024-02-01T01:00:00,2\n", "M1,2024-02-01T01:02:02,2\n"
        )
    )
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    output = export_selection(
        workspace,
        result,
        tmp_path / "report",
        {
            "view_selection": asdict(ResultSelection("2024-02")),
            "include_xlsx": False,
            "include_timestamp_adjustments": True,
        },
        lambda: None,
    )
    with (output / "timestamp-adjustments.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["Tệp nguồn"] == "mdms.csv"
    assert rows[0]["SHA-256 nguồn"] == result["sources"][1]["sha256"]
    assert rows[0]["Thời điểm nguồn"] == "2024-02-01T01:02:02"
    assert rows[0]["Thời điểm sau hiệu chỉnh"] == "2024-02-01T01:00:00"
    assert rows[0]["Độ lệch về sau so với mốc (giây)"] == "122.0"
    manifest = json.loads((output / "export-manifest.json").read_text())
    assert "timestamp-adjustments.csv" in {item["name"] for item in manifest["files"]}


def test_timestamp_audit_export_escapes_spreadsheet_formula_and_checks_cache(tmp_path):
    request = request_files(tmp_path)
    cmis, source = tmp_path / "cmis.csv", tmp_path / "mdms.csv"
    cmis.write_text(cmis.read_text().replace("M1", "=M1"))
    source.write_text(
        source.read_text()
        .replace("M1,", "=M1,")
        .replace("2024-02-01T01:00:00,2\n", "2024-02-01T01:02:02,2\n")
    )
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    options = {
        "view_selection": asdict(ResultSelection("2024-02")),
        "include_xlsx": False,
        "include_timestamp_adjustments": True,
    }
    output = export_selection(
        workspace, result, tmp_path / "report", options, lambda: None
    )
    with (output / "timestamp-adjustments.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        row = next(csv.DictReader(stream))
    assert row["Mã công tơ"] == "'=M1"
    result["import"]["database_hash"] = "0" * 64
    with pytest.raises(ValueError, match="cache is missing or changed"):
        export_selection(
            workspace, result, tmp_path / "rejected", options, lambda: None
        )
    assert not (tmp_path / "rejected").exists()
