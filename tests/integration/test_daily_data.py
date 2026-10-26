import copy
from datetime import date

import pytest
from test_pipeline import request_files

from load_research.application.daily import load_daily
from load_research.application.pipeline import ResearchCancelled, run_study
from load_research.calendar import ResearchCalendar
from load_research.workspace import Workspace, file_hash


def test_daily_artifacts_and_legacy_reconstruction_match_without_external_files(
    tmp_path,
):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    assert result["industry_universe"] == {"2024-02": ["01"]}
    saved = load_daily(workspace, result, "2024-02", ("01",))
    assert saved["01"]["cohort_size"] == 2
    assert saved["01"]["source"][0] == [6] * 48
    assert saved["01"]["processed"][2] == [3] * 48
    assert (
        saved["01"]["day_types"][2]
        == ResearchCalendar().classify(date(2024, 2, 3)).value
    )
    for path in request.all_paths():
        path.unlink()
    legacy = copy.deepcopy(result)
    legacy["cells"][0].pop("daily_artifact")
    snapshot = workspace.safe_path(f"runs/{result['run_id']}/artifacts/result.json")
    before = file_hash(snapshot)
    rebuilt = load_daily(workspace, legacy, "2024-02", ("01",))
    assert rebuilt == saved
    assert file_hash(snapshot) == before


def test_daily_checksum_and_cancellation_are_enforced(tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path))
    with pytest.raises(ResearchCancelled):
        load_daily(
            workspace,
            result,
            "2024-02",
            ("01",),
            check=lambda: (_ for _ in ()).throw(ResearchCancelled()),
        )
    artifact = result["cells"][0]["daily_artifact"]
    path = workspace.safe_path(f"runs/{result['run_id']}/artifacts/{artifact}")
    path.write_text("{}")
    with pytest.raises(ValueError, match="checksum|changed|hash"):
        load_daily(workspace, result, "2024-02", ("01",))
