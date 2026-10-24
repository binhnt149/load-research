from datetime import datetime

import pytest

from load_research.importers.catalog import load_catalog
from load_research.importers.metering import MeterRecord
from load_research.infrastructure.store import IntervalStore


def record(value=10.0, meter="M1", minute=0):
    return MeterRecord(
        "0001",
        "01",
        meter,
        datetime(2024, 2, 1, 0, minute),
        30,
        value,
        False,
        True,
        "source",
        2,
    )


def test_duplicate_intervals_are_deduplicated_across_batches(tmp_path):
    with IntervalStore(tmp_path / "data.duckdb", memory_limit_mb=128) as store:
        store.append([record()])
        store.append([record()])
        store.validate()
        assert store.raw_count == 2
        assert list(store.iter_records("2024-02"))[0].energy_kwh == 10
        assert len(list(store.iter_records("2024-02"))) == 1


def test_conflicting_duplicates_never_silently_choose_last(tmp_path):
    with IntervalStore(tmp_path / "data.duckdb", memory_limit_mb=128) as store:
        store.append([record(10), record(20)])
        with pytest.raises(ValueError, match="conflicting"):
            store.validate()


def test_additive_meters_require_all_contributors_for_a_complete_interval(tmp_path):
    catalog = load_catalog(
        [
            {
                "customer_id": "0001",
                "industry_code": "01",
                "meter_id": meter,
                "meter_role": "additive",
            }
            for meter in ("M1", "M2")
        ],
        "NPC",
    )
    with IntervalStore(tmp_path / "data.duckdb", memory_limit_mb=128) as store:
        store.append([record(10, "M1"), record(20, "M2"), record(5, "M1", 30)])
        store.validate()
        grid = next(store.iter_customer_months("2024-02", 30, catalog))
        assert grid.customer.customer_id == "0001"
        assert grid.values[0, 0] == 30
        assert grid.values[0, 1] != grid.values[0, 1]  # NaN: M2 is missing
        assert grid.values.shape == (29, 48)
