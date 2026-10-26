import pytest

from load_research.importers.catalog import load_billing, load_catalog
from load_research.importers.tables import read_rows
from load_research.input_errors import InputDataError


@pytest.mark.parametrize(
    ("loader", "contents", "technical"),
    [
        (
            load_catalog,
            "customer_id,industry_code,meter_id\n0001,,M1\n",
            "industry_code",
        ),
        (
            load_catalog,
            "customer_id,industry_code,meter_id,sampling_weight\n0001,01,M1,-1\n",
            "finite",
        ),
        (
            load_billing,
            "industry_code,year_month,billing_energy,unit,billing_basis\n01,2024-02,10,,calendar_month\n",
            "unit",
        ),
        (
            load_billing,
            "industry_code,year_month,billing_energy,unit,billing_basis\n01,2024-02,NaN,kWh,calendar_month\n",
            "finite",
        ),
    ],
)
def test_invalid_catalog_and_billing_rows_keep_source_location(
    tmp_path, loader, contents, technical
):
    source = tmp_path / "dữ liệu.csv"
    source.write_text(contents, encoding="utf-8")
    with pytest.raises(InputDataError) as caught:
        loader(read_rows(source), "NPC")
    assert technical in str(caught.value)
    assert caught.value.source_context == {"path": str(source), "row": 2, "sheet": None}


def test_global_mapping_conflict_is_not_attributed_to_an_arbitrary_last_row(tmp_path):
    source = tmp_path / "cmis.csv"
    source.write_text(
        "customer_id,industry_code,meter_id\n0001,01,M1\n0002,01,M1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ambiguous") as caught:
        load_catalog(read_rows(source), "NPC")
    assert not getattr(caught.value, "source_context", {})
