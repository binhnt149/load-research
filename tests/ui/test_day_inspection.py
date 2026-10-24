from load_research.ui.inspection import DayInspectionDialog


def test_inspection_dialog_shows_before_after_and_audit_fields(qtbot):
    details = {
        "run_id": "a" * 32,
        "customer_id": "0001",
        "date": "2024-02-01",
        "day_type": "weekday",
        "interval_minutes": 30,
        "eligible": True,
        "original_month_coverage": 0.99,
        "rows": [
            {
                "slot_index": index + 1,
                "original_kwh": None if index == 2 else 2,
                "repaired_kwh": 2,
                "estimated": index == 2,
                "method": "linear" if index == 2 else "source",
            }
            for index in range(48)
        ],
    }
    dialog = DayInspectionDialog(details)
    qtbot.addWidget(dialog)
    assert dialog.model.rowCount() == 48
    assert dialog.model.records[2]["method"] == "linear"
    assert len(dialog.canvas.figure.axes[0].lines) == 2
