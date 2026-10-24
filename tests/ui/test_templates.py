from PySide6.QtWidgets import QFileDialog


def test_template_dialog_exports_a_readable_workbook_and_reports_existing_files(
    qtbot, tmp_path, monkeypatch
):
    from load_research.importers.tables import read_rows
    from load_research.ui.template_dialog import TemplateDialog

    dialog = TemplateDialog(category="cmis")
    qtbot.addWidget(dialog)
    path = tmp_path / "cmis.xlsx"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args: (str(path), "Excel (*.xlsx)")
    )
    dialog.save_button.click()
    assert list(read_rows(path))[0]["customer_id"] == "000001"
    before = path.read_bytes()
    dialog.save_button.click()
    assert "đã tồn tại" in dialog.status.text()
    assert path.read_bytes() == before


def test_each_source_group_opens_its_own_template_category(qtbot, monkeypatch):
    from load_research.ui.forms import ResearchForm
    from load_research.ui.template_dialog import TemplateDialog

    seen = []
    monkeypatch.setattr(
        TemplateDialog, "exec", lambda dialog: seen.append(dialog.category)
    )
    form = ResearchForm()
    qtbot.addWidget(form)
    for selector in (form.cmis, form.mdms, form.billing, form.calendar_files):
        selector.template_button.click()
    assert seen == ["cmis", "mdms", "billing", "calendar"]
