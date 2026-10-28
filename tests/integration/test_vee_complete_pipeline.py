import csv
import json

from test_pipeline import request_files

from load_research.application.daily import load_daily
from load_research.application.inspection import inspect_customer
from load_research.application.pipeline import run_study
from load_research.workspace import Workspace


def test_complete_pipeline_uses_only_complete_customers_and_keeps_audit_offline(
    tmp_path,
):
    request = request_files(tmp_path)
    path = tmp_path / "mdms.csv"
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([*rows[0], "source_quality_flag"])
        for row in rows[1:]:
            if row[0] == "M1" and row[1].startswith("2024-02-01"):
                continue
            if row[0] == "M2" and row[1] == "2024-02-02T01:00:00":
                writer.writerow([row[0], row[1], "", "outage"])
            else:
                writer.writerow([*row, "actual"])
    workspace = Workspace.create(tmp_path / "project")
    result = run_study(workspace, request)
    assert result["quality"][0]["excluded"]["0002"] == "incomplete_vee"
    assert {member["customer_id"] for member in result["cells"][0]["members"]} == {
        "0001"
    }
    daily = load_daily(workspace, result, "2024-02", ("01",))["01"]
    assert daily["cohort_size"] == 1
    assert all(value is not None for day in daily["processed"] for value in day)
    assert daily["processed"][0] == [2] * 48
    journal = workspace.safe_path(result["quality_journal"]["path"])
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    filled = [
        event
        for event in events
        if event["customer_id"] == "0001" and event["date"] == "2024-02-01"
    ]
    assert len(filled) == 48 and {event["method"] for event in filled} == {
        "same_type_unscaled"
    }
    assert all(event["donor_dates"] for event in filled)
    for source in request.all_paths():
        source.unlink()
    detail = inspect_customer(
        workspace, result["run_id"], "0001", "2024-02-01", "2024-02-01"
    )
    assert all(
        row["original_kwh"] is None and row["repaired_kwh"] == 2
        for row in detail["rows"]
    )
    blocked = inspect_customer(
        workspace, result["run_id"], "0002", "2024-02-02", "2024-02-02"
    )
    assert (
        blocked["rows"][2]["repair_blocked"]
        and blocked["rows"][2]["repaired_kwh"] is None
    )
