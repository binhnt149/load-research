import pytest

from load_research.error_messages import format_error
from load_research.input_errors import InputDataError


@pytest.mark.parametrize(
    ("technical", "words"),
    [
        ("ambiguous or empty table header", ("tiêu đề", "trùng", "trống")),
        ("mapping references a missing source column", ("ánh xạ", "cột", "nguồn")),
        ("billing basis must be explicitly declared", ("cơ sở kỳ", "thương phẩm")),
        ("MDMS unit differs from declared source unit", ("đơn vị", "MDMS", "khai báo")),
        ("number must be finite and non-negative", ("hữu hạn", "không âm")),
        ("DBSCAN requires an explicit eps", ("DBSCAN", "eps", "bán kính")),
        ("min_customers must be a positive integer", ("Cỡ mẫu", "nguyên dương")),
        ("could not convert string to float: 'abc'", ("abc", "số", "không hợp lệ")),
        (
            "Invalid isoformat string: '2026-13-02'",
            ("2026-13-02", "ngày", "YYYY-MM-DD"),
        ),
    ],
)
def test_validation_errors_have_vietnamese_causes_and_actions(technical, words):
    message = format_error(technical)
    assert technical not in message
    for word in words:
        assert word.lower() in message.lower()


def test_worker_context_and_machine_field_are_present_in_localized_error():
    error = InputDataError(
        "missing or invalid industry_code",
        {"path": r"C:\du-lieu\CMIS.xlsx", "row": 12, "sheet": "Tháng 2"},
    )
    message = format_error(error)
    assert "CMIS.xlsx" in message and "dòng 12" in message
    assert "Tháng 2" in message and "Mã ngành nghề" in message
    assert "industry_code" in message and "missing or invalid" not in message
    assert str(error) == "missing or invalid industry_code"


def test_metering_row_wrapper_preserves_line_and_translates_inner_cause():
    message = format_error("invalid source row 5: missing meter mapping key")
    assert "dòng 5" in message and "công tơ" in message
    assert "invalid source row" not in message


def test_encoding_and_unknown_errors_have_safe_vietnamese_fallbacks():
    assert "UTF-8" in format_error("codec details", error_type="UnicodeDecodeError")
    message = format_error("unknown third-party reader exception")
    assert "unknown third-party" not in message
    assert "kiểm tra" in message.lower()
