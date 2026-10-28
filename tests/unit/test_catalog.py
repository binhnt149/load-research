from datetime import datetime

import pytest

from load_research.importers.catalog import load_billing, load_catalog


def test_catalog_uses_measurement_point_when_meter_id_contains_only_whitespace():
    catalog = load_catalog(
        [
            {
                "customer_id": "0001",
                "industry_code": "01",
                "meter_id": "   ",
                "measurement_point_id": "M01",
            }
        ],
        "NPC",
    )
    assert catalog.links[0].meter_id == "M01"


def test_old_catalog_policy_preserves_whitespace_key_rejection():
    with pytest.raises(ValueError, match="meter mapping"):
        load_catalog(
            [
                {
                    "customer_id": "0001",
                    "industry_code": "01",
                    "meter_id": " ",
                    "measurement_point_id": "M01",
                }
            ],
            "NPC",
            meter_key_policy="legacy",
        )


def test_customer_meter_mapping_preserves_ids_weights_and_effective_dates():
    catalog = load_catalog(
        [
            {
                "customer_id": "000123",
                "industry_code": "01",
                "meter_id": "old",
                "valid_to": "2024-02-15",
                "sampling_weight": "2",
            },
            {
                "customer_id": "000123",
                "industry_code": "01",
                "meter_id": "new",
                "valid_from": "2024-02-15",
                "sampling_weight": "2",
            },
        ],
        "NPC",
    )
    customer = catalog.resolve("old", datetime(2024, 2, 14))
    assert customer.customer_id == "000123"
    assert customer.weight == 2
    assert catalog.resolve("new", datetime(2024, 2, 15)).industry_code == "01"
    with pytest.raises(ValueError, match="mapping"):
        catalog.resolve("old", datetime(2024, 2, 15))


def test_ambiguous_meter_mapping_and_invalid_weights_are_rejected():
    rows = [
        {"customer_id": cid, "industry_code": "01", "meter_id": "same"}
        for cid in ("001", "002")
    ]
    with pytest.raises(ValueError, match="mapping"):
        load_catalog(rows, "NPC")
    with pytest.raises(ValueError):
        load_catalog(
            [
                {
                    "customer_id": "001",
                    "industry_code": "01",
                    "meter_id": "a",
                    "sampling_weight": "nan",
                }
            ],
            "NPC",
        )


def test_billing_requires_unique_scope_month_and_period_basis():
    row = {
        "industry_code": "01",
        "year_month": "2024-02",
        "billing_energy": "2",
        "unit": "MWh",
        "billing_basis": "calendar_month",
    }
    totals = load_billing([row], "NPC")
    assert totals[("01", "2024-02")].energy_kwh == 2000
    with pytest.raises(ValueError, match="duplicate"):
        load_billing([row, row], "NPC")
    with pytest.raises(ValueError, match="scope"):
        load_billing([{**row, "organization_scope": "other"}], "NPC")
    with pytest.raises(ValueError, match="basis"):
        load_billing([{**row, "billing_basis": ""}], "NPC")


@pytest.mark.parametrize("energy", ["-1", "nan", "inf"])
def test_invalid_industry_totals_cannot_enter_scaling(energy):
    with pytest.raises(ValueError):
        load_billing(
            [
                {
                    "industry_code": "01",
                    "year_month": "2024-02",
                    "billing_energy": energy,
                    "unit": "kWh",
                    "billing_basis": "calendar_month",
                }
            ],
            "NPC",
        )
