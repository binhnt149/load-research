"""Real malformed inputs must produce useful Vietnamese UI diagnostics."""

import re

import openpyxl
import pytest

from load_research.application.models import SourceInput, StudyRequest
from load_research.domain.config import RunConfig, SourceOptions
from load_research.ui.source_preview import SourcePreviewDialog
from load_research.ui.window import MainWindow
from load_research.workspace import Workspace


def test_csv_preview_explains_wrong_column_count_and_source_line(qtbot, tmp_path):
    source = tmp_path / "mdms-sai-so-cot.csv"
    source.write_text("meter_id,value\nM001,10,20\n", encoding="utf-8")
    dialog = SourcePreviewDialog(str(source))
    qtbot.addWidget(dialog)
    message = dialog.status.text().lower()

    assert dialog.model.rowCount() == 0
    assert "cột" in message
    assert re.search(r"dòng\s*2\b", message)
    assert "tiêu đề" in message
    assert "column count differs" not in message
    assert "source row" not in message


def test_excel_preview_names_the_missing_sheet_in_vietnamese(qtbot, tmp_path):
    source = tmp_path / "cmis.xlsx"
    book = openpyxl.Workbook()
    book.active.title = "Dữ liệu"
    book.active.append(["customer_id", "industry_code", "meter_id"])
    book.active.append(["0001", "01", "M001"])
    book.save(source)
    book.close()
    missing_sheet = "Sản lượng tháng không có"
    dialog = SourcePreviewDialog(str(source), sheet=missing_sheet)
    qtbot.addWidget(dialog)
    message = dialog.status.text().lower()

    assert dialog.model.rowCount() == 0
    assert missing_sheet.lower() in message
    assert "không tồn tại" in message or "không tìm thấy" in message
    assert "trang tính" in message or "sheet" in message
    assert "requested excel sheet does not exist" not in message


def test_csv_preview_explains_duplicate_column_names_in_vietnamese(qtbot, tmp_path):
    source = tmp_path / "cmis-trung-tieu-de.csv"
    source.write_text("customer_id,customer_id\n0001,01\n", encoding="utf-8")
    dialog = SourcePreviewDialog(str(source))
    qtbot.addWidget(dialog)
    message = dialog.status.text().lower()

    assert dialog.model.rowCount() == 0
    assert "trùng" in message
    assert "tiêu đề" in message or "tên cột" in message
    assert "ambiguous or empty table header" not in message


@pytest.mark.parametrize(
    ("missing_field", "field_description"),
    [("customer_id", "khách hàng"), ("industry_code", "ngành")],
)
def test_research_ui_identifies_missing_cmis_field_and_source_location(
    qtbot, tmp_path, missing_field, field_description
):
    cmis = tmp_path / "cmis-thieu-du-lieu.csv"
    values = {"customer_id": "0001", "industry_code": "01", "meter_id": "M001"}
    values[missing_field] = ""
    cmis.write_text(
        "customer_id,industry_code,meter_id\n" + ",".join(values.values()) + "\n",
        encoding="utf-8",
    )
    mdms = tmp_path / "mdms.csv"
    mdms.write_text(
        "meter_id,timestamp,value,source_quality_flag\n"
        "M001,2024-02-01T00:00:00,1,actual\n",
        encoding="utf-8",
    )
    billing = tmp_path / "billing.csv"
    billing.write_text(
        "industry_code,year_month,billing_energy,unit,billing_basis\n"
        "01,2024-02,10000,kWh,calendar_month\n",
        encoding="utf-8",
    )
    request = StudyRequest(
        RunConfig(
            periods=("2024-02",), scope="NPC", min_customers=1, memory_limit_mb=128
        ),
        (str(cmis),),
        (SourceInput(str(mdms), SourceOptions(values_already_scaled=True)),),
        (str(billing),),
    )
    workspace = Workspace.create(tmp_path / "project")
    window = MainWindow()
    qtbot.addWidget(window)
    window.open_project(workspace.root)
    window.set_request(request)
    window.start_research()
    try:
        qtbot.waitUntil(lambda: window.last_error is not None, timeout=30000)
        qtbot.waitUntil(lambda: not window.job.is_running, timeout=30000)
        window.poll_job()
        message = window.status_label.text().lower()

        assert field_description in message
        assert missing_field in message
        assert "thiếu" in message or "trống" in message
        assert cmis.name in message
        assert re.search(r"dòng\s*2\b", message)
        assert "missing or invalid" not in message
    finally:
        if window.job is not None:
            window.job.close()
