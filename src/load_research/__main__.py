"""Desktop entry point; multiprocessing children never create a QApplication."""

import multiprocessing
import sys


def main() -> int:
    multiprocessing.freeze_support()
    from load_research.runtime import prepare_runtime_cache

    prepare_runtime_cache()
    if len(sys.argv) > 1:
        from load_research.cli import main as cli_main

        return cli_main(sys.argv[1:])
    from load_research.ui.bootstrap import prepare_qt_plugins

    prepare_qt_plugins()
    from PySide6.QtWidgets import QApplication

    from load_research.ui.window import MainWindow

    application = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
