from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from load_research.ui.forms import FileList


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
