from datetime import datetime

from test_pipeline import request_files

from load_research.application.inspection import inspect_day
from load_research.application.pipeline import run_study
from load_research.workspace import Workspace


def test_saved_run_can_explain_original_repaired_values_and_reason(tmp_path):
    request = request_files(tmp_path)
    path = tmp_path / "mdms.csv"
    path.write_text(path.read_text().replace("M1,2024-02-01T01:00:00,2\n", ""))
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    import json

    audit = json.loads(
        workspace.safe_path(result["quality_journal"]["path"])
        .read_text()
        .splitlines()[0]
    )
    assert audit["run_id"] == result["run_id"]
    assert audit["actor"] == "application" and audit["config_hash"]
    assert audit["recorded_at"] and audit["old_quality"] == "missing"
    # Inspection uses immutable catalog/cache, even if original external sources are offline.
    for source in request.all_paths():
        source.unlink()
    details = inspect_day(
        workspace, result["run_id"], "0001", datetime(2024, 2, 1).date()
    )
    assert details["rows"][2]["original_kwh"] is None
    assert details["rows"][2]["repaired_kwh"] == 2
    assert details["rows"][2]["method"] == "linear"
    assert details["eligible"]
