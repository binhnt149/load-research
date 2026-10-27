import pytest
from test_pipeline import request_files

from load_research.application.inspection import inspect_customer
from load_research.application.pipeline import run_study
from load_research.workspace import Workspace


def test_customer_range_preserves_real_values_missing_repair_and_excluded_status(
    tmp_path,
):
    request = request_files(tmp_path)
    path = tmp_path / "mdms.csv"
    path.write_text(path.read_text().replace("M1,2024-02-01T01:00:00,2\n", ""))
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    for source in request.all_paths():
        source.unlink()
    details = inspect_customer(
        workspace, result["run_id"], "0001", "2024-02-01", "2024-02-02"
    )
    assert len(details["rows"]) == 96
    assert details["rows"][2]["original_kwh"] is None
    assert details["rows"][2]["repaired_kwh"] == 2
    assert details["rows"][2]["method"] == "linear"
    assert details["rows"][48]["date"] == "2024-02-02"
    assert (
        details["rows"][48]["repaired_kwh"] == 2
    )  # customer, not industry or scaled total
    with pytest.raises(ValueError, match="khách hàng"):
        inspect_customer(
            workspace, result["run_id"], "missing", "2024-02-01", "2024-02-01"
        )
    cache = workspace.safe_path(f"cache/{result['import']['key']}.duckdb")
    with cache.open("ab") as stream:
        stream.write(b"corrupted")
    with pytest.raises(ValueError, match="cache"):
        inspect_customer(
            workspace, result["run_id"], "0001", "2024-02-01", "2024-02-01"
        )


def test_customer_with_partial_meter_mapping_is_still_viewable_without_faking_zeros(
    tmp_path,
):
    request = request_files(tmp_path)
    path = tmp_path / "cmis.csv"
    path.write_text(
        "customer_id,industry_code,meter_id,valid_from\n0001,01,M1,2024-02-15T00:00:00\n0002,01,M2,\n"
    )
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    details = inspect_customer(
        workspace, result["run_id"], "0001", "2024-02-14", "2024-02-15"
    )
    assert all(
        r["original_kwh"] is None and r["repaired_kwh"] is None
        for r in details["rows"][:48]
    )
    assert details["rows"][48]["original_kwh"] == 2
    assert details["rows"][48]["repaired_kwh"] == 2
