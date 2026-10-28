from dataclasses import replace

from test_results import result_data

from load_research.domain.config import RunConfig, SourceOptions
from load_research.ui.forms import ConfigForm, ExportDialog, SourceDialog
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


def test_result_shows_timestamp_audit_preview_and_export_option(qtbot):
    result = result_data()
    result["sources"] = [{"path": "/private/path/mdms.csv", "sha256": "abc"}]
    result["import"] = {
        "timestamp_adjustments": 1,
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
    export = ExportDialog(view)
    qtbot.addWidget(export)
    assert not export.options()["include_timestamp_adjustments"]
    export.timestamp_adjustments.setChecked(True)
    assert export.options()["include_timestamp_adjustments"]
