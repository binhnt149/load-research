import pytest

from load_research.presentation import field_label, format_value, translated_value


def test_result_labels_use_electricity_terms_and_interval_numbers():
    assert field_label("billing_kwh") == "Điện năng thương phẩm (kWh)"
    assert field_label("alpha") == "Hệ số suy rộng α"
    assert field_label("slot_02") == "Chu kỳ 02"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("day_type", "weekday", "Ngày làm việc"),
        ("status", "missing_billing", "Thiếu điện năng thương phẩm"),
        ("billing_basis", "calendar_month", "Tháng dương lịch"),
        ("method", "like_day", "Bù bằng ngày tương đồng"),
        ("eligible", False, "Không"),
    ],
)
def test_result_enums_are_localized_by_field(field, value, expected):
    assert translated_value(field, value) == expected


def test_identifiers_and_numeric_report_data_are_never_translated():
    assert translated_value("customer_id", "weekday") == "weekday"
    assert translated_value("industry_code", "valid") == "valid"
    assert translated_value("billing_kwh", 1234.5) == 1234.5
    assert translated_value("weight", 0.25) == 0.25


def test_display_formats_fractions_and_unavailable_data_explicitly():
    assert format_value("estimated_fraction", 0.125) == "12,5%"
    assert format_value("billing_kwh", 1234.5) == "1.234,5"
    assert format_value("alpha", None) == "—"


def test_all_saved_method_parameters_have_vietnamese_labels():
    from load_research.domain.config import RunConfig

    config = RunConfig(periods=("2024-02",), scope="NPC")
    assert not [key for key in config.to_dict() if field_label(key) == key]


def test_task_log_uses_vietnamese_status_without_raw_worker_schema():
    from load_research.presentation import event_text

    text = event_text(
        {"stage": "finished", "run_id": "abc", "status": "completed_with_warnings"}
    )
    assert "Hoàn thành" in text and "cảnh báo" in text
    assert "stage" not in text and "completed_with_warnings" not in text
