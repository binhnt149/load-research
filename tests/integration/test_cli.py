import json
import subprocess
import sys


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-m", "load_research", *map(str, args)],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_demo_cli_runs_from_portable_request_to_balanced_report(tmp_path):
    demo = tmp_path / "demo"
    generated = invoke(
        "demo", "--output", demo, "--customers", 20, "--period", "2024-02"
    )
    assert generated.returncode == 0, generated.stderr
    payload = json.loads((demo / "request.json").read_text())
    assert payload["cmis_paths"] == ["cmis.csv"]
    completed = invoke(
        "run",
        "--request",
        demo / "request.json",
        "--project",
        tmp_path / "project",
        "--export",
        tmp_path / "report",
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "completed"
    assert (tmp_path / "report" / "profiles.xlsx").is_file()
    manifest = json.loads((tmp_path / "report" / "export-manifest.json").read_text())
    assert manifest["status"] == "completed"


def test_demo_refuses_existing_directory_without_overwriting(tmp_path):
    (tmp_path / "important.txt").write_text("preserve")
    result = invoke("demo", "--output", tmp_path)
    assert result.returncode != 0
    assert (tmp_path / "important.txt").read_text() == "preserve"
