import json
import os

import pytest
from test_pipeline import request_files

from load_research.application.jobs import ResearchJob
from load_research.application.pipeline import run_study
from load_research.backup import backup_project
from load_research.domain.config import RunConfig
from load_research.workspace import Workspace


def crash_while_holding_project_lock(root, events):
    workspace = Workspace.open(root)
    run_id = workspace.create_run(RunConfig(periods=("2024-02",), scope="NPC"), [])
    with workspace.writer():
        workspace.set_status(run_id, "running")
        events.put({"stage": "started", "run_id": run_id})
        events.close()
        events.join_thread()
        os._exit(7)


def test_close_recovers_lock_and_run_of_a_worker_that_already_crashed(tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    job = ResearchJob(workspace.root)
    job.process = job.context.Process(
        target=crash_while_holding_project_lock, args=(workspace.root, job.events)
    )
    job.process.start()
    job.join(30)
    assert job.process.exitcode == 7
    assert (workspace.root / ".writer.lock").is_file()
    job.close()
    assert not (workspace.root / ".writer.lock").exists()
    assert workspace.read_run(job.run_id)["status"] == "failed"


@pytest.mark.parametrize("qt_separators", [False, True])
def test_relocated_windows_paths_are_resolved_on_another_os(tmp_path, qt_separators):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    backup = Workspace.open(
        backup_project(workspace, tmp_path / "backup", include_sources=True)
    )
    run = backup.read_run(result["run_id"])
    remap = {
        source["path"]: "C:\\research\\" + source["path"].split("/")[-1]
        for source in run["sources"]
    }
    for source in run["sources"]:
        source["path"] = remap[source["path"]]
    payload = run["details"]
    for key in ("cmis_paths", "billing_paths"):
        payload["request"][key] = [remap[path] for path in payload["request"][key]]
    for source in payload["request"]["mdms_sources"]:
        source["path"] = remap[source["path"]]
    if qt_separators:
        for key in ("cmis_paths", "billing_paths"):
            payload["request"][key] = [
                path.replace("\\", "/").lower() for path in payload["request"][key]
            ]
        for source in payload["request"]["mdms_sources"]:
            source["path"] = source["path"].replace("\\", "/").lower()
    with backup.connection() as database:
        database.execute(
            "UPDATE runs SET sources=?, details=? WHERE id=?",
            (json.dumps(run["sources"]), json.dumps(payload), result["run_id"]),
        )
    backup.verify_sources(result["run_id"])
    assert all(
        path.is_file() for path in backup.request_for_run(result["run_id"]).all_paths()
    )
