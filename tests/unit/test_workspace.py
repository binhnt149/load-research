import json

import pytest

from load_research.domain.config import RunConfig
from load_research.workspace import Workspace, WorkspaceBusy


def test_run_snapshot_and_sources_survive_reopening(tmp_path):
    source = tmp_path / "nguồn.csv"
    source.write_text("customer_id\n000123\n")
    project = tmp_path / "Nghiên cứu"
    workspace = Workspace.create(project)
    config = RunConfig(periods=("2024-02",), scope="NPC")
    run_id = workspace.create_run(config, [source])
    reopened = Workspace.open(project)
    assert reopened.read_run(run_id)["config"] == config.to_dict()
    reopened.verify_sources(run_id)
    source.write_text("customer_id\nchanged\n")
    with pytest.raises(ValueError, match="changed"):
        reopened.verify_sources(run_id)


def test_artifacts_are_atomic_immutable_and_traversal_is_rejected(tmp_path):
    workspace = Workspace.create(tmp_path / "study")
    run_id = workspace.create_run(RunConfig(periods=("2024-02",), scope="NPC"), [])
    path = workspace.save_artifact(run_id, "profiles.json", {"energy": [1.0, 2.0]})
    assert json.loads(path.read_text()) == {"energy": [1.0, 2.0]}
    with pytest.raises(FileExistsError):
        workspace.save_artifact(run_id, "profiles.json", {"energy": [0]})
    with pytest.raises(ValueError):
        workspace.save_artifact(run_id, "../../outside.json", {})
    assert workspace.load_artifact(run_id, "profiles.json")["energy"] == [1.0, 2.0]


def test_only_one_writer_can_acquire_a_project(tmp_path):
    workspace = Workspace.create(tmp_path / "study")
    with workspace.writer():
        with pytest.raises(WorkspaceBusy):
            with Workspace.open(workspace.root).writer():
                pytest.fail("a second writer must never acquire the lock")
    with workspace.writer():
        assert workspace.root.is_dir()


def test_symlink_artifact_cannot_escape_workspace(tmp_path):
    workspace = Workspace.create(tmp_path / "study")
    run_id = workspace.create_run(RunConfig(periods=("2024-02",), scope="NPC"), [])
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace.root / "runs" / run_id / "artifacts").rmdir()
    (workspace.root / "runs" / run_id / "artifacts").symlink_to(outside)
    with pytest.raises(ValueError):
        workspace.save_artifact(run_id, "escaped.json", {})
    assert not list(outside.iterdir())


def test_terminal_run_rejects_new_artifacts(tmp_path):
    from load_research.domain.config import RunConfig
    from load_research.workspace import Workspace

    workspace = Workspace.create(tmp_path / "project")
    run_id = workspace.create_run(RunConfig(periods=("2024-02",), scope="NPC"), [])
    workspace.set_status(run_id, "completed")
    with pytest.raises(ValueError, match="immutable"):
        workspace.save_artifact(run_id, "late.json", {})
