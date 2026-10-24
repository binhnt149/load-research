import csv
import json

import openpyxl
import pytest

from load_research.exports import export_study, safe_csv_text


def study():
    vector = [10.0, 20.0] * 24
    return {
        "run_id": "a" * 32,
        "status": "completed",
        "method_version": "class-profile-v1",
        "config": {"interval_minutes": 30, "scope": "NPC"},
        "calendar": {},
        "quality": [],
        "sources": [],
        "cells": [
            {
                "industry_code": "=cmd()",
                "year_month": "2024-02",
                "billing_basis": "calendar_month",
                "day_counts": {"weekday": 29},
                "result": {
                    "status": "valid",
                    "sample": {"weekday": vector},
                    "energy": {"weekday": vector},
                    "contributions": {"weekday": {"group_1": vector}},
                    "sample_contributions": {"weekday": {"group_1": vector}},
                    "billing_kwh": 20880,
                    "background_kwh": 20880,
                    "alpha": 1,
                    "diagnostics": {},
                },
                "members": [],
            }
        ],
    }


def test_export_24_periods_preserves_energy_and_has_verifiable_manifest(tmp_path):
    destination = export_study(
        study(), tmp_path / "export", interval_minutes=60, unit="kW"
    )
    with (destination / "profiles.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert float(rows[0]["slot_01"]) == 30
    assert "slot_24" in rows[0] and "slot_25" not in rows[0]
    assert rows[0]["industry_code"] == "'=cmd()"
    workbook = openpyxl.load_workbook(
        destination / "profiles.xlsx", read_only=True, data_only=False
    )
    assert {
        "Readme",
        "Profiles",
        "Cluster_Contributions",
        "Quality",
        "Balance_Checks",
        "Parameters",
    } <= set(workbook.sheetnames)
    assert all(cell.data_type != "f" for row in workbook["Profiles"] for cell in row)
    workbook.close()
    manifest = json.loads((destination / "export-manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert any(entry["name"] == "profiles.csv" for entry in manifest["files"])
    assert (destination / "methodology.md").is_file()


def test_existing_destination_and_unsupported_resolution_are_rejected(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        export_study(study(), existing)
    data = study()
    data["config"]["interval_minutes"] = 60
    with pytest.raises(ValueError, match="resolution"):
        export_study(data, tmp_path / "no", interval_minutes=30)
    assert not (tmp_path / "no").exists()


def test_xlsx_overflow_is_not_silently_truncated(tmp_path, monkeypatch):
    monkeypatch.setattr("load_research.exports.EXCEL_MAX_ROWS", 4)
    with pytest.raises(ValueError, match="Excel"):
        export_study(study(), tmp_path / "large", layout="long")
    assert not (tmp_path / "large").exists()
    assert export_study(
        study(), tmp_path / "csv-only", layout="long", include_xlsx=False
    ).is_dir()


@pytest.mark.parametrize("text", ["=1+1", " +calc", "-calc", "@calc", "\t=calc"])
def test_csv_formula_injection_is_neutralized(text):
    assert safe_csv_text(text).startswith("'")


def test_filtered_export_keeps_cluster_display_names_and_selection_metadata(tmp_path):
    import copy

    data = study()
    second = copy.deepcopy(data["cells"][0])
    second["industry_code"] = "02"
    second["cluster_names"] = {"weekday": {"group_1": "Ca ngày"}}
    data["cells"].append(second)
    exported = export_study(
        data,
        tmp_path / "selection",
        industry_codes=("02",),
        periods=("2024-02",),
        day_types=("weekday",),
        include_xlsx=False,
    )
    with (exported / "profiles.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["industry_code"] for row in rows} == {"02"}
    assert next(row for row in rows if row["cluster_id"])["cluster_name"] == "Ca ngày"
    manifest = json.loads((exported / "export-manifest.json").read_text())
    assert manifest["filters"]["industry_codes"] == ["02"]


def test_cancelled_export_does_not_publish_incomplete_directory(tmp_path):
    from load_research.application.pipeline import ResearchCancelled

    with pytest.raises(ResearchCancelled):
        export_study(study(), tmp_path / "cancelled", cancelled=lambda: True)
    assert not (tmp_path / "cancelled").exists()


def test_quality_export_keeps_columns_present_only_in_later_months(tmp_path):
    data = study()
    data["quality"] = [
        {"period": "2024-01"},
        {"period": "2024-02", "original_valid": 1392},
    ]
    exported = export_study(data, tmp_path / "report")
    with (exported / "quality-summary.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert rows[1]["original_valid"] == "1392"


@pytest.mark.parametrize("root", ["/private/local-user/", "C:\\Users\\local-user\\"])
def test_export_carries_industry_names_calendar_and_source_semantics(tmp_path, root):
    data = study()
    data["cells"][0]["industry_name"] = "Cơ khí"
    data["calendar"] = {"holidays": ["2024-02-10"], "overrides": {}}
    data["request"] = {
        "config": data["config"],
        "cmis_paths": [root + "cmis.csv"],
        "mdms_sources": [
            {
                "path": root + "mdms.csv",
                "options": {"timestamp_convention": "end"},
            }
        ],
    }
    exported = export_study(data, tmp_path / "report")
    saved = json.loads((exported / "run-config.json").read_text())
    assert saved["calendar"]["holidays"] == ["2024-02-10"]
    assert saved["mdms_sources"][0]["options"]["timestamp_convention"] == "end"
    assert saved["cmis_paths"] == ["cmis.csv"]
    with (exported / "profiles.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert next(csv.DictReader(stream))["industry_name"] == "Cơ khí"


def test_member_export_respects_day_and_cluster_filters(tmp_path):
    data = study()
    data["cells"][0]["members"] = [
        {"customer_id": "a", "day_type": "weekday", "cluster_id": "group_1"},
        {"customer_id": "b", "day_type": "sunday", "cluster_id": "group_2"},
    ]
    exported = export_study(
        data,
        tmp_path / "report",
        include_members=True,
        day_types=("weekday",),
        cluster_ids=("group_1",),
    )
    with (exported / "cluster-members.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        assert [row["customer_id"] for row in csv.DictReader(stream)] == ["a"]
