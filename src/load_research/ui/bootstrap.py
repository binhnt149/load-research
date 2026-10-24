"""Expose trusted macOS platform plugins outside managed hidden .venv trees.

Some managed workspaces recursively mark ignored .venv files UF_HIDDEN. Qt's
plugin scanner excludes those files, even though the loader can open them.
Use a process-owned temporary copy; never modify installed vendor files.
"""

import shutil
import stat
import sys
import tempfile
from pathlib import Path

_plugins: tempfile.TemporaryDirectory | None = None


def prepare_qt_plugins() -> int:
    global _plugins
    if sys.platform != "darwin":
        return 0
    import PySide6
    from PySide6.QtCore import QCoreApplication, QLibraryInfo

    package = Path(PySide6.__file__).resolve().parent
    plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)).resolve()
    if not plugins.is_relative_to(package):
        return 0  # native bundles may use Contents/PlugIns; retain Qt discovery
    platform_plugins = plugins / "platforms"
    if not platform_plugins.is_dir():
        return 0
    hidden = any(part.startswith(".") for part in package.parts) or any(
        path.stat().st_flags & stat.UF_HIDDEN for path in platform_plugins.iterdir()
    )
    if not hidden:
        return 0
    if _plugins is None:
        _plugins = tempfile.TemporaryDirectory(prefix="load-research-qt-")
        destination = Path(_plugins.name) / "platforms"
        destination.mkdir()
        for path in platform_plugins.iterdir():
            if (
                path.is_file()
                and not path.is_symlink()
                and path.resolve().is_relative_to(package)
            ):
                shutil.copyfile(path, destination / path.name)
    QCoreApplication.addLibraryPath(_plugins.name)
    return 1
