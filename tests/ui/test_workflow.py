from dataclasses import replace
from datetime import date

import pytest

from load_research.application.models import SourceInput, StudyRequest
from load_research.calendar import DayType, ResearchCalendar
from load_research.domain.config import RunConfig, SourceOptions
from load_research.ui.forms import CalendarDialog, SourcePreviewDialog
from load_research.ui.window import MainWindow
from load_research.workspace import Workspace


def test_desktop_restores_all_request_parameters_and_source_semantics(qtbot, tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    request = StudyRequest(
        replace(RunConfig(periods=("2024-02",), scope="NPC"), min_customers=1),
        (str(tmp_path / "cmis.csv"),),
        (
            SourceInput(
                str(tmp_path / "mdms.csv"),
                SourceOptions(values_already_scaled=False, multiplier=10),
            ),
        ),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_project(workspace.root)
    window.set_request(request)
    restored = window.build_request()
    assert restored.config == request.config
    assert restored.mdms_sources[0].options.multiplier == 10
    assert not restored.mdms_sources[0].options.values_already_scaled
    assert window.start_button.isEnabled()


def test_desktop_rejects_invalid_month_before_starting_worker(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.form.config_form.periods.setText("2024-13")
    with pytest.raises(ValueError):
        window.build_request()
    assert window.job is None


def test_source_preview_is_bounded_and_preserves_identifiers(qtbot, tmp_path):
    path = tmp_path / "source.csv"
    path.write_text("customer_id,value\n" + "0001,3\n" * 200)
    dialog = SourcePreviewDialog(str(path), limit=50)
    qtbot.addWidget(dialog)
    assert dialog.model.rowCount() == 50
    assert dialog.model.records[0]["customer_id"] == "0001"


def test_calendar_editor_keeps_overrides_and_method_parameters_are_editable(qtbot):
    calendar = ResearchCalendar(overrides={date(2024, 2, 10): DayType.HOLIDAY})
    dialog = CalendarDialog(calendar)
    qtbot.addWidget(dialog)
    assert dialog.value().classify(date(2024, 2, 10)) == DayType.HOLIDAY
    window = MainWindow()
    qtbot.addWidget(window)
    form = window.form.config_form
    form.fractions["donor_common_fraction"].setValue(0.7)
    form.parameters["mad_factor"].setValue(8)
    assert form.value().mad_factor == 8
    assert form.value().donor_common_fraction == 0.7


def test_new_mdms_files_require_source_semantics_before_running(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.form.cmis.set_paths(["cmis.csv"])
    window.form.mdms.set_paths(["mdms.csv"])
    with pytest.raises(ValueError, match="MDMS"):
        window.build_request()
