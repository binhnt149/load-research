import pytest

from load_research.domain.config import RunConfig
from load_research.workspace import Workspace


def test_cluster_label_history_does_not_modify_completed_result(tmp_path):
    workspace = Workspace.create(tmp_path / "project")
    run_id = workspace.create_run(RunConfig(periods=("2024-02",), scope="NPC"), [])
    result = {
        "cells": [
            {
                "industry_code": "01",
                "year_month": "2024-02",
                "clusters": {"weekday": {"assignments": {"001": "group_1"}}},
            }
        ]
    }
    workspace.save_artifact(run_id, "result.json", result)
    workspace.set_status(run_id, "completed")
    workspace.add_cluster_label(
        run_id,
        "01",
        "2024-02",
        "weekday",
        "group_1",
        "Ca ngày",
        "Đã đối chiếu vận hành",
    )
    workspace.add_cluster_label(
        run_id,
        "01",
        "2024-02",
        "weekday",
        "group_1",
        "Ca 1",
        "Chuyên viên hiệu chỉnh tên",
    )
    assert [
        row["label"]
        for row in Workspace.open(workspace.root).list_cluster_labels(run_id)
    ] == ["Ca ngày", "Ca 1"]
    assert workspace.load_artifact(run_id, "result.json") == result
    with pytest.raises(ValueError):
        workspace.add_cluster_label(
            run_id, "01", "2024-02", "weekday", "group_1", "Ca 2", ""
        )
    with pytest.raises(ValueError):
        workspace.add_cluster_label(
            run_id, "01", "2024-02", "weekday", "not-existing", "Ca 2", "Xác nhận"
        )
