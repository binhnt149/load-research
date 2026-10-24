from test_pipeline import request_files

from load_research.application.jobs import ResearchJob
from load_research.application.pipeline import run_study
from load_research.workspace import Workspace


def test_spawned_worker_publishes_references_and_progress(tmp_path):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    job = ResearchJob(workspace.root)
    try:
        job.start(request)
        job.join(30)
        assert not job.is_running
        events = job.poll()
        assert any(event["stage"] == "finished" for event in events)
        assert not any(
            "cells" in event for event in events
        )  # raw/result arrays stay on disk
        assert workspace.list_runs()[0]["status"] == "completed_with_warnings"
    finally:
        job.close()


def test_cooperative_cancellation_reaches_a_terminal_status(tmp_path):
    request = request_files(tmp_path)
    workspace = Workspace.create(tmp_path / "project")
    job = ResearchJob(workspace.root)
    try:
        job.start(request)
        job.cancel()
        job.join(30)
        assert not job.is_running
        assert workspace.list_runs()[0]["status"] == "cancelled"
        assert any(event["stage"] == "cancelled" for event in job.poll())
    finally:
        job.close()


def test_export_worker_uses_saved_run_and_writes_selected_report(tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path))
    job = ResearchJob(workspace.root)
    try:
        job.start_export(
            result["run_id"],
            tmp_path / "report",
            {"include_xlsx": False, "interval_minutes": 60},
        )
        job.join(30)
        assert not job.is_running
        assert any(event["stage"] == "exported" for event in job.poll())
        assert (tmp_path / "report" / "profiles.csv").is_file()
        assert workspace.read_run(result["run_id"])["status"] == result["status"]
    finally:
        job.close()


def test_verification_worker_reports_changed_sources_without_losing_saved_results(
    tmp_path,
):
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path))
    (tmp_path / "mdms.csv").write_text("changed")
    job = ResearchJob(workspace.root)
    try:
        job.start_verification()
        job.join(30)
        events = job.poll()
        assert (
            next(event for event in events if event["stage"] == "sources_verified")[
                "changed_count"
            ]
            == 1
        )
        assert workspace.load_artifact(result["run_id"], "result.json")["cells"]
    finally:
        job.close()
