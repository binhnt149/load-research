import json

import pytest

from load_research.application.components import import_components, load_components
from load_research.workspace import Workspace


def test_import_keeps_revision_and_checksum_without_altering_runs(tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    path = tmp_path / "catalog.csv"
    path.write_text(
        "Mã ngành nghề,Tên ngành nghề,Mã thành phần,Tên thành phần phụ tải\n001,Cơ khí,CN,Công nghiệp\n",
        encoding="utf-8-sig",
    )
    first = import_components(workspace, path)
    assert first["rows"][0]["industry_code"] == "001"
    path.write_text(
        path.read_text(encoding="utf-8-sig").replace("CN,Công nghiệp", "DV,Dịch vụ"),
        encoding="utf-8",
    )
    second = import_components(workspace, path)
    path.unlink()
    reopened = Workspace.open(workspace.root)
    assert load_components(reopened)["checksum"] == second["checksum"]
    assert (
        load_components(reopened, first["revision"])["rows"][0]["component_code"]
        == "CN"
    )
    assert workspace.list_runs() == []
    with workspace.connection() as db:
        db.execute(
            "UPDATE component_catalogs SET payload=? WHERE revision=?",
            (json.dumps([]), second["revision"]),
        )
    with pytest.raises(ValueError, match="checksum"):
        load_components(reopened)


def test_cancelled_or_invalid_import_preserves_previous_catalog(tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    path = tmp_path / "catalog.csv"
    path.write_text(
        "industry_code,industry_name,component_code,component_name\n01,Cơ khí,CN,Công nghiệp\n"
    )

    def cancel():
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        import_components(workspace, path, check=cancel)
    assert load_components(workspace) is None


def test_import_worker_updates_loaded_result_and_export_pins_catalog(qtbot, tmp_path):
    from test_pipeline import request_files

    from load_research.application.pipeline import run_study
    from load_research.ui.window import MainWindow

    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request_files(tmp_path))
    path = tmp_path / "components.csv"
    path.write_text(
        "industry_code,industry_name,component_code,component_name\n01,Cơ khí,CN,Công nghiệp\n"
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.workspace = workspace
    window.load_run(result["run_id"])
    window.start_auxiliary(
        "components", {"path": str(path), "sheet": None, "delimiter": ","}
    )
    qtbot.waitUntil(
        lambda: window.job is not None and not window.job.is_running, timeout=30000
    )
    window.poll_job()
    assert window.last_error is None, window.last_error_details
    view = window.results
    view.component_selector.setCurrentIndex(view.component_selector.findData("CN"))
    assert view.current_view["component_code"] == "CN"
    options = {**view.export_options(selected=True), "include_xlsx": False}
    window.start_export(tmp_path / "export", options)
    qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
    window.poll_job()
    assert window.last_error is None, window.last_error_details
    manifest = json.loads((tmp_path / "export" / "export-manifest.json").read_text())
    assert manifest["component_catalog"]["revision"] == 1
    assert (
        manifest["views"][0]["component_catalog_checksum"]
        == load_components(workspace)["checksum"]
    )


def test_backup_retains_imported_catalog_without_original_file(tmp_path):
    from load_research.backup import backup_project

    workspace = Workspace.create(tmp_path / "project")
    path = tmp_path / "catalog.csv"
    path.write_text(
        "industry_code,industry_name,component_code,component_name\n001,Cơ khí,CN,Công nghiệp\n"
    )
    catalog = import_components(workspace, path)
    path.unlink()
    backup = backup_project(workspace, tmp_path / "backup", include_sources=False)
    assert load_components(Workspace.open(backup)) == catalog


def test_catalog_result_from_previous_project_cannot_change_new_project(
    qtbot, tmp_path
):
    from load_research.ui.window import MainWindow

    old = Workspace.create(tmp_path / "old")
    new = Workspace.create(tmp_path / "new")
    path = tmp_path / "catalog.csv"
    path.write_text(
        "industry_code,industry_name,component_code,component_name\n001,Cơ khí,CN,Công nghiệp\n"
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.workspace = old
    window.start_auxiliary("components", {"path": str(path)})
    window.workspace = new
    qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
    window.poll_job()
    assert window.results.component_catalog is None
    assert load_components(new) is None
