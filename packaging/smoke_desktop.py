"""Launch an actual Qt desktop, open a computed run and capture the widget."""

import argparse
import json
import multiprocessing
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    arguments = parser.parse_args()
    from load_research.runtime import prepare_runtime_cache

    prepare_runtime_cache()
    from load_research.ui.bootstrap import prepare_qt_plugins

    prepare_qt_plugins()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from load_research.ui.window import MainWindow

    application = QApplication([])
    window = MainWindow()
    window.open_project(arguments.project)
    window.load_run(window.workspace.list_runs()[0]["id"])
    window.show()
    failures = []

    def capture() -> None:
        try:
            application.processEvents()
            arguments.screenshot.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(arguments.screenshot)):
                raise RuntimeError("could not save desktop screenshot")
            if (
                window.results.table_model.rowCount() not in (24, 48)
                or window.last_error
            ):
                raise RuntimeError(
                    window.last_error or "computed curve was not rendered"
                )
            print(
                json.dumps(
                    {
                        "qt_platform": application.platformName(),
                        "rows": window.results.table_model.rowCount(),
                        "screenshot": str(arguments.screenshot),
                        "status": window.status_label.text(),
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as error:
            failures.append(str(error))
        finally:
            window.close()
            application.quit()

    QTimer.singleShot(1800, capture)
    application.exec()
    if failures:
        raise RuntimeError(failures[0])
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
