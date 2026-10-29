import pytest

from load_research.importers.catalog import Catalog, load_catalog


@pytest.mark.parametrize(
    ("extra", "group"),
    [
        ({"annual_energy_kwh": "10000"}, "B"),
        ({"annual_energy_kwh": "10000000"}, "E"),
        ({"annual_energy_kwh": "500"}, None),
        ({"consumption_stratum": "c"}, "C"),
        ({"annual_energy_kwh": "50000", "consumption_stratum": "B"}, "B"),
        ({}, None),
    ],
)
def test_customer_stratum_from_explicit_group_or_annual_energy(extra, group):
    row = {"customer_id": "1", "industry_code": "01", "meter_id": "M1", **extra}
    catalog = load_catalog([row], "NPC")
    assert catalog.links[0].customer.consumption_stratum == group
    assert (
        Catalog.from_dict(catalog.to_dict()).links[0].customer
        == catalog.links[0].customer
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"annual_energy_kwh": "10000", "consumption_stratum": "A"},
        {"consumption_stratum": "F"},
        {"annual_energy_kwh": "-1"},
    ],
)
def test_invalid_or_contradictory_customer_stratum_is_rejected(extra):
    row = {"customer_id": "1", "industry_code": "01", "meter_id": "M1", **extra}
    with pytest.raises(ValueError):
        load_catalog([row], "NPC")
