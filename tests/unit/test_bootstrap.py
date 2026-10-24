from PySide6.QtCore import QLibraryInfo

from load_research.ui.bootstrap import prepare_qt_plugins


def test_native_bundle_plugin_location_keeps_qt_default_discovery(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        QLibraryInfo,
        "path",
        staticmethod(lambda _kind: str(tmp_path / "Contents" / "PlugIns")),
    )
    assert prepare_qt_plugins() == 0
