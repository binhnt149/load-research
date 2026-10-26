import os
import sys
import tempfile
from pathlib import Path

from load_research.ui.bootstrap import prepare_qt_plugins

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Windows offscreen uses QFreeTypeFontDatabase, which scans fontDir rather than
# the native Windows font database. Empty font discovery produces box metrics.
# Qt 6.12: src/gui/text/qplatformfontdatabase.cpp::fontDir (QT_QPA_FONTDIR).
if sys.platform == "win32" and os.environ["QT_QPA_PLATFORM"] == "offscreen":
    os.environ.setdefault(
        "QT_QPA_FONTDIR", str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts")
    )
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "load-research-matplotlib")
)
prepare_qt_plugins()
