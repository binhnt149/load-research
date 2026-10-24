from importlib.metadata import PackageNotFoundError

from load_research.application.pipeline import runtime_versions


def test_frozen_runtime_records_versions_without_distribution_metadata(monkeypatch):
    def absent(_name):
        raise PackageNotFoundError

    monkeypatch.setattr("load_research.application.pipeline.version", absent)
    versions = runtime_versions()
    assert set(versions) == {"numpy", "scikit-learn", "duckdb", "pyarrow", "PySide6"}
    assert all(value and value[0].isdigit() for value in versions.values())
