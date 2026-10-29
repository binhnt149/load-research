from dataclasses import replace

from test_results import result_data

from load_research.domain.config import RunConfig, SourceOptions
from load_research.ui.forms import ConfigForm, ExportDialog, ResearchForm, SourceDialog
from load_research.ui.results import ResultsView


def test_timestamp_policy_is_visible_editable_and_restored(qtbot, tmp_path):
    dialog = SourceDialog(
        str(tmp_path / "mdms.csv"), SourceOptions(values_already_scaled=True)
    )
    qtbot.addWidget(dialog)
    assert dialog.alignment.currentData() == "floor"
    dialog.alignment.setCurrentIndex(dialog.alignment.findData("strict"))
    assert dialog.value().timestamp_alignment == "strict"


def test_vee_policy_is_visible_editable_and_saved(qtbot):
    form = ConfigForm()
    qtbot.addWidget(form)
    assert form.vee_completion.currentData() == "complete"
    old = replace(RunConfig(periods=("2026-01",), scope="NPC"), vee_completion="legacy")
    form.set_config(old)
    assert form.vee_completion.currentData() == "legacy"
    form.vee_completion.setCurrentIndex(form.vee_completion.findData("complete"))
    assert form.value().vee_completion == "complete"


def test_collision_policy_is_visible_and_restored(qtbot):
    form = ConfigForm()
    qtbot.addWidget(form)
    assert form.collision_policy.currentData() == "prefer_nearest"
    old = replace(
        RunConfig(periods=("2026-01",), scope="NPC"), collision_policy="reject"
    )
    form.set_config(old)
    assert form.collision_policy.currentData() == "reject"
    assert form.value().collision_policy == "reject"


def test_stratum_configuration_can_be_selected_and_restored(qtbot, tmp_path):
    from load_research.application.models import SourceInput, StudyRequest

    request = StudyRequest(
        RunConfig(periods=("2026-01",), scope="NPC"),
        (str(tmp_path / "cmis.xlsx"),),
        (
            SourceInput(
                str(tmp_path / "mdms.csv"), SourceOptions(values_already_scaled=True)
            ),
        ),
        strata_paths=(str(tmp_path / "strata.xlsx"),),
    )
    form = ResearchForm()
    qtbot.addWidget(form)
    form.set_request(request)
    assert form.strata.paths() == request.strata_paths
    assert form.build_request().strata_paths == request.strata_paths


def test_results_display_stratum_curves_and_factors(qtbot):
    result = result_data()
    cell = result["cells"][0]
    cell["stratification"] = {
        "strata": {
            "A": {
                "population_count": 10,
                "reference_energy_kwh": 50000,
                "allocated_billing_kwh": 20880,
                "cohort_size": 1,
                "result": cell["result"],
            }
        }
    }
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    assert view.strata_model.rowCount() == 1
    assert view.strata_model.records[0]["stratum"] == "A"
    assert any(
        "Nhóm sản lượng A" in line.get_label()
        for line in view.canvas.figure.axes[0].lines
    )
    view.clear_result()
    assert view.strata_model.rowCount() == 0


def test_result_shows_timestamp_audit_preview_and_export_option(qtbot):
    result = result_data()
    result["sources"] = [{"path": "/private/path/mdms.csv", "sha256": "abc"}]
    result["import"] = {
        "timestamp_adjustments": 1,
        "timestamp_conflict_groups": 1,
        "timestamp_conflicts_preview": [
            {
                "source_id": "abc",
                "source_row": 5,
                "selected": False,
                "offset_seconds": 120,
            }
        ],
        "timestamp_adjustments_preview": [
            {
                "source_id": "abc",
                "source_row": 2,
                "customer_id": "001",
                "meter_id": "M01",
                "original_timestamp": "2026-01-01T10:32:02",
                "aligned_timestamp": "2026-01-01T10:30:00",
                "offset_seconds": 122,
            }
        ],
    }
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_result(result)
    assert view.timestamp_model.records[0]["source_name"] == "mdms.csv"
    assert view.timestamp_model.records[0]["offset_seconds"] == 122
    assert "1" in view.data_tabs.tabText(10)
    assert view.conflicts_model.records[0]["source_name"] == "mdms.csv"
    assert not view.conflicts_model.records[0]["selected"]
    export = ExportDialog(view)
    qtbot.addWidget(export)
    assert not export.options()["include_timestamp_adjustments"]
    export.timestamp_adjustments.setChecked(True)
    assert export.options()["include_timestamp_adjustments"]
