from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from load_research.ui.forms import FileList


def test_preview_recovers_from_missing_file_and_never_displays_stale_rows(
    qtbot, tmp_path
):
    from load_research.ui.forms import SourcePreviewDialog

    path = tmp_path / "source.csv"
    dialog = SourcePreviewDialog(str(path))
    qtbot.addWidget(dialog)
    assert dialog.model.rowCount() == 0
    assert "Không đọc được" in dialog.status.text()
    path.write_text("customer_id,value\n0001,2\n")
    dialog.reload_button.click()
    assert dialog.model.records[0]["customer_id"] == "0001"
    path.write_text("id,id\n1,2\n")
    dialog.reload_button.click()
    assert dialog.model.rowCount() == 0
    assert "Không đọc được" in dialog.status.text()


def test_preview_can_switch_delimiter_and_excel_sheet(qtbot, tmp_path):
    import openpyxl

    from load_research.ui.forms import SourcePreviewDialog

    path = tmp_path / "source.csv"
    path.write_text("customer_id;value\n0001;2\n")
    csv_dialog = SourcePreviewDialog(str(path))
    qtbot.addWidget(csv_dialog)
    csv_dialog.delimiter.setCurrentIndex(csv_dialog.delimiter.findData(";"))
    assert csv_dialog.model.columnCount() == 2
    assert csv_dialog.model.records[0]["customer_id"] == "0001"
    book = openpyxl.Workbook()
    book.active.title = "Cover"
    book.active.append(["Description"])
    data = book.create_sheet("Dữ liệu")
    data.append(["customer_id", "value"])
    data.append(["0001", 2])
    xlsx = tmp_path / "source.xlsx"
    book.save(xlsx)
    excel_dialog = SourcePreviewDialog(str(xlsx))
    qtbot.addWidget(excel_dialog)
    excel_dialog.sheet.setCurrentText("Dữ liệu")
    assert excel_dialog.model.records[0]["customer_id"] == "0001"


def test_header_only_and_corrupt_excel_preview_have_explanatory_states(qtbot, tmp_path):
    from load_research.ui.forms import SourcePreviewDialog

    path = tmp_path / "empty.csv"
    path.write_text("customer_id,value\n")
    dialog = SourcePreviewDialog(str(path))
    qtbot.addWidget(dialog)
    assert dialog.model.columnCount() == 2
    assert "chưa có dòng" in dialog.status.text()
    corrupt = tmp_path / "bad.xlsx"
    corrupt.write_bytes(b"not an Excel archive")
    error_dialog = SourcePreviewDialog(str(corrupt))
    qtbot.addWidget(error_dialog)
    assert error_dialog.model.rowCount() == 0
    assert "Không đọc được" in error_dialog.status.text()


def test_choosing_files_selects_the_new_file_and_preview_emits_its_path(
    qtbot, monkeypatch
):
    selector = FileList("CMIS")
    qtbot.addWidget(selector)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileNames", lambda *args: (["khách hàng.csv"], "")
    )
    selector.select_files()
    assert selector.list.currentItem() is not None
    assert selector.list.currentItem().text() == "khách hàng.csv"
    with qtbot.waitSignal(selector.preview_requested) as signal:
        selector.preview_button.click()
    assert signal.args == ["khách hàng.csv"]


def test_file_names_are_readable_while_actions_keep_the_full_source_path(
    qtbot, tmp_path
):
    selector = FileList("CMIS")
    qtbot.addWidget(selector)
    path = str(tmp_path / "khách hàng.csv")
    selector.set_paths([path])
    assert selector.list.currentItem().text() == "khách hàng.csv"
    assert selector.list.currentItem().toolTip() == path
    assert selector.paths() == (path,)
    with qtbot.waitSignal(selector.preview_requested) as signal:
        selector.preview_button.click()
    assert signal.args == [path]


def test_mdms_semantics_editor_receives_the_full_source_path(
    qtbot, tmp_path, monkeypatch
):
    from load_research.ui.forms import ResearchForm, SourceDialog

    form = ResearchForm()
    qtbot.addWidget(form)
    path = str(tmp_path / "source.csv")
    form.mdms.set_paths([path])
    seen = []
    monkeypatch.setattr(SourceDialog, "exec", lambda dialog: seen.append(dialog.path))
    form.edit_source()
    assert seen == [path]


def test_preview_button_state_follows_loading_and_removing_files(qtbot):
    selector = FileList("MDMS")
    qtbot.addWidget(selector)
    assert not selector.preview_button.isEnabled()
    selector.set_paths(["first.csv", "second.csv"])
    assert selector.preview_button.isEnabled()
    assert selector.list.currentRow() == 0
    selector.remove_selected()
    assert selector.paths() == ("second.csv",)
    assert selector.list.currentRow() == 0
    selector.remove_selected()
    assert not selector.preview_button.isEnabled()


def test_duplicate_and_cancelled_file_picks_keep_a_working_current_file(
    qtbot, monkeypatch
):
    selector = FileList("CMIS")
    qtbot.addWidget(selector)
    selector.set_paths(["first.csv"])
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        lambda *args: (["first.csv", "second.csv", "second.csv"], ""),
    )
    selector.select_files()
    assert selector.paths() == ("first.csv", "second.csv")
    assert selector.list.currentItem().text() == "second.csv"
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([], ""))
    selector.select_files()
    assert selector.list.currentItem().text() == "second.csv"


def test_double_click_opens_preview_for_that_file(qtbot):
    selector = FileList("MDMS")
    qtbot.addWidget(selector)
    selector.set_paths(["first.csv", "second.csv"])
    selector.show()
    item = selector.list.item(1)
    rect = selector.list.visualItemRect(item)
    with qtbot.waitSignal(selector.preview_requested) as signal:
        qtbot.mouseClick(
            selector.list.viewport(), Qt.MouseButton.LeftButton, pos=rect.center()
        )
        qtbot.mouseDClick(
            selector.list.viewport(), Qt.MouseButton.LeftButton, pos=rect.center()
        )
    assert signal.args == ["second.csv"]
