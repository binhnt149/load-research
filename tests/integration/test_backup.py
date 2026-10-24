import pytest
from test_pipeline import request_files

from load_research.application.pipeline import run_study
from load_research.backup import backup_project
from load_research.workspace import Workspace


def test_backup_can_verify_and_reuse_sources_after_original_files_are_removed(tmp_path):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    destination = backup_project(workspace, tmp_path / "backup", include_sources=True)
    for path in request.all_paths():
        path.unlink()
    restored = Workspace.open(destination)
    restored.verify_sources(result["run_id"])
    reused = restored.request_for_run(result["run_id"])
    assert run_study(restored, reused)["cells"] == result["cells"]


def test_backup_never_recurses_into_itself_or_copies_changed_sources(tmp_path):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    run_study(workspace, request)
    with pytest.raises(ValueError, match="outside"):
        backup_project(workspace, workspace.root / "backup", include_sources=False)
    (tmp_path / "mdms.csv").write_text("changed")
    with pytest.raises(ValueError, match="source"):
        backup_project(workspace, tmp_path / "changed", include_sources=True)
    assert not (tmp_path / "changed").exists()
