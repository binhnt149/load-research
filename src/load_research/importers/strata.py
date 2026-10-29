"""Read population statistics by industry and annual-consumption stratum."""

from dataclasses import dataclass
from pathlib import Path

from load_research.importers.catalog import number, required_text
from load_research.importers.tables import read_rows
from load_research.input_errors import source_row


@dataclass(frozen=True)
class StratumStatistics:
    industry_code: str
    stratum: str
    population_count: int
    reference_energy_kwh: float
    mean_energy_kwh: float | None
    standard_deviation_kwh: float | None
    coefficient_of_variation: float | None


FIELDS = {
    "industry_code": "Mã ngành nghề",
    "stratum": "Nhóm sản lượng",
    "population_count": "Số lượng khách hàng",
    "reference_energy_kwh": "Tổng Sản lượng",
    "mean_energy_kwh": "Trung bình sản lượng\n(Tổng sản lượng/số lượng khách hàng)",
    "standard_deviation_kwh": "Độ lệch chuẩn",
    "coefficient_of_variation": "Độ lệch chuẩn/Trung bình sản lượng",
}


def _optional_number(value: str) -> float | None:
    return number(value) if value.strip() else None


def load_stratum_configuration(
    path: Path, *, sheet: str | None = None, delimiter: str = ","
) -> dict[tuple[str, str], StratumStatistics]:
    result = {}
    for row in read_rows(path, mapping=FIELDS, sheet=sheet, delimiter=delimiter):
        with source_row(row):
            industry = required_text(row, "industry_code")
            stratum = required_text(row, "stratum").upper()
            if stratum not in {"A", "B", "C", "D", "E"}:
                raise ValueError("invalid consumption stratum; expected A to E")
            count = number(row["population_count"])
            if not count.is_integer() or count <= 0:
                raise ValueError("stratum population count must be a positive integer")
            key = (industry, stratum)
            if key in result:
                raise ValueError("duplicate industry and consumption stratum")

            result[key] = StratumStatistics(
                industry,
                stratum,
                int(count),
                number(row["reference_energy_kwh"]),
                _optional_number(row["mean_energy_kwh"]),
                _optional_number(row["standard_deviation_kwh"]),
                _optional_number(row["coefficient_of_variation"]),
            )
    if not result:
        raise ValueError("stratum configuration is empty")
    return result
