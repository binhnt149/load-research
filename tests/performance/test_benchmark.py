import json

import pytest

from load_research.benchmark import run_benchmark


@pytest.mark.performance
def test_bounded_benchmark_records_actual_resources_and_balances(tmp_path):
    report = run_benchmark(tmp_path / "benchmark", customers=20, months=1, year=2025)
    assert report["status"] == "completed"
    assert report["dimensions"]["interval_values"] == 20 * 31 * 48
    assert report["measured"]["peak_rss_bytes"] > 0
    assert report["measured"]["analysis_export_seconds"] > 0
    assert report["measured"]["final_disk_bytes"] > 0
    assert json.loads((tmp_path / "benchmark" / "benchmark-report.json").read_text())[
        "machine"
    ]["os"]


def test_full_scale_benchmark_never_silently_runs_from_small_defaults(tmp_path):
    with pytest.raises(ValueError, match="full-size"):
        run_benchmark(tmp_path / "large", customers=7000, months=12, year=2025)
