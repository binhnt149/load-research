import os
import tempfile
from pathlib import Path

from load_research.ui.bootstrap import prepare_qt_plugins

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "load-research-matplotlib")
)
prepare_qt_plugins()
