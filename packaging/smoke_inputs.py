"""Exercise source input widgets on a real Qt runtime and capture their states."""

import argparse
import json
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("ci-results/ui-refresh"))
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    from load_research.runtime import prepare_runtime_cache

    prepare_runtime_cache()
    from load_research.ui.bootstrap import prepare_qt_plugins

    prepare_qt_plugins()
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from load_research.ui.source_preview import SourcePreviewDialog
    from load_research.ui.template_dialog import TemplateDialog
    from load_research.ui.window import MainWindow

    app = QApplication([])
    args.output.mkdir(parents=True, exist_ok=True)
    window = MainWindow()
    window.show()
    screenshots = []

    def capture(widget, name):
        app.processEvents()
        path = args.output / f"{name}.png"
        if not widget.grab().save(str(path)):
            raise RuntimeError(f"Could not capture {name}")
        screenshots.append(path.name)

    capture(window, "empty")
    for selector, key in zip(
        (
            window.form.cmis,
            window.form.mdms,
            window.form.billing,
            window.form.calendar_files,
        ),
        ("cmis", "mdms_wide_48", "billing", "calendar"),
        strict=True,
    ):
        selector.set_paths([str(Path("templates") / f"{key}.csv")])
    for width, height in ((1240, 860), (1024, 768)):
        window.resize(width, height)
        app.processEvents()
        if window.width() != width or window.height() != height:
            raise RuntimeError(
                "A page minimum size prevents the requested laptop viewport"
            )
        viewport = window.tabs.widget(0).viewport()
        for selector in (
            window.form.cmis,
            window.form.mdms,
            window.form.billing,
            window.form.calendar_files,
        ):
            button = selector.preview_button
            if not viewport.rect().contains(
                button.mapTo(viewport, button.rect().bottomRight())
            ):
                raise RuntimeError("A source preview action is clipped")
        capture(window, f"sources-{width}")
    window.form.cmis.add_button.setFocus()
    QTest.keyClick(window.form.cmis.add_button, Qt.Key.Key_Tab)
    if app.focusWidget() is not window.form.cmis.remove_button:
        raise RuntimeError("Source actions are not reachable by keyboard")
    window.form.options_toggle.click()
    window.tabs.widget(0).ensureWidgetVisible(window.form.cmis_sheet)
    capture(window, "advanced")
    window.form.options_toggle.click()
    preview = SourcePreviewDialog("templates/cmis.csv", parent=window)
    preview.show()
    if preview.model.records[0]["customer_id"] != "000001":
        raise RuntimeError("Source preview lost the customer identifier")
    capture(preview, "preview")
    preview.close()
    with tempfile.TemporaryDirectory(prefix="load-research-preview-") as folder:
        source = Path(folder) / "source.csv"
        source.write_text("customer_id;value\n000001;2\n", encoding="utf-8")
        preview = SourcePreviewDialog(str(source), parent=window)
        preview.delimiter.setCurrentIndex(preview.delimiter.findData(";"))
        if preview.model.columnCount() != 2:
            raise RuntimeError("CSV delimiter change did not refresh the preview")
        source.write_text("id;id\n1;2\n", encoding="utf-8")
        preview.reload_button.click()
        preview.show()
        if preview.model.rowCount() or "Không đọc được" not in preview.status.text():
            raise RuntimeError("A bad source kept stale rows or hid its error")
        capture(preview, "preview-error")
        preview.close()
    for category in ("cmis", "mdms"):
        dialog = TemplateDialog(category=category, parent=window)
        dialog.show()
        capture(dialog, f"template-{category}")
        dialog.tabs.setCurrentIndex(1)
        capture(dialog, f"template-{category}-guide")
        dialog.close()
    if args.result:
        window.results.set_result(json.loads(args.result.read_text(encoding="utf-8")))
        window.tabs.setCurrentIndex(2)
        capture(window, "results")
        if window.results.table_model.rowCount() not in (24, 48):
            raise RuntimeError("The computed result did not render")
    window.close()
    print(
        json.dumps(
            {
                "status": "passed",
                "platform": app.platformName(),
                "screenshots": screenshots,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
