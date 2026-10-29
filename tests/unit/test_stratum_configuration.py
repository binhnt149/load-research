import csv

import pytest
from openpyxl import Workbook

from load_research.importers.strata import load_stratum_configuration

HEADERS = [
    "Mã ngành nghề",
    "Nhóm sản lượng",
    "Số lượng khách hàng",
    "Tổng Sản lượng",
    "Trung bình sản lượng\n(Tổng sản lượng/số lượng khách hàng)",
    "Độ lệch chuẩn",
    "Độ lệch chuẩn/Trung bình sản lượng",
]


def test_load_population_strata_from_user_workbook_layout(tmp_path):
    path = tmp_path / "configuration.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.append(HEADERS)
    sheet.append([1000, "A", 2, 6000, 3000, 1000, 1 / 3])
    sheet.append([1000, "B", 3, 90000, 30000, 2000, 1 / 15])
    book.save(path)
    rows = load_stratum_configuration(path)
    assert set(rows) == {("1000", "A"), ("1000", "B")}
    assert rows[("1000", "A")].population_count == 2
    assert rows[("1000", "A")].reference_energy_kwh == 6000
    assert rows[("1000", "A")].standard_deviation_kwh == 1000


@pytest.mark.parametrize(
    "row",
    [
        ["1000", "F", 2, 6000, 3000, 1000, 1 / 3],
        ["1000", "A", 2.5, 6000, 3000, 1000, 1 / 3],
        ["1000", "A", 2, -1, 3000, 1000, 1 / 3],
        ["1000", "A", 2, "NaN", 3000, 1000, 1 / 3],
    ],
)
def test_reject_invalid_stratum_statistics(tmp_path, row):
    path = tmp_path / "configuration.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerow(row)
    with pytest.raises(ValueError):
        load_stratum_configuration(path)


def test_reject_duplicate_industry_stratum(tmp_path):
    path = tmp_path / "configuration.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows([["1000", "A", 2, 6000, 3000, 1000, 1 / 3]] * 2)
    with pytest.raises(ValueError, match="duplicate"):
        load_stratum_configuration(path)


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_user_can_download_and_import_stratum_template(tmp_path, suffix):
    from load_research.input_templates import write_template

    path = write_template("strata", tmp_path / f"strata.{suffix}")
    rows = load_stratum_configuration(path)
    assert set(rows) == {("01", "A"), ("01", "B")}
