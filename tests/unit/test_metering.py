from datetime import datetime

import pytest

from load_research.domain.config import SourceOptions
from load_research.importers.catalog import load_catalog
from load_research.importers.metering import canonicalize


def sample_catalog():
    return load_catalog(
        [{"customer_id": "000123", "industry_code": "01", "meter_id": "M01"}], "NPC"
    )


def test_mdms_uses_measurement_point_when_meter_id_contains_only_whitespace():
    options = SourceOptions(values_already_scaled=True)
    records = list(
        canonicalize(
            [
                {
                    "meter_id": "   ",
                    "measurement_point_id": "M01",
                    "timestamp": "2024-02-01T00:00",
                    "value": "1",
                }
            ],
            sample_catalog(),
            options,
        )
    )
    assert records[0].meter_id == "M01"
    assert records[0].customer_id == "000123"


def test_old_meter_key_policy_preserves_rejection_of_whitespace_meter_id():
    rows = [
        {
            "meter_id": "   ",
            "measurement_point_id": "M01",
            "timestamp": "2024-02-01T00:00",
            "value": "1",
        }
    ]
    issues = []
    assert (
        list(
            canonicalize(
                rows,
                sample_catalog(),
                SourceOptions(values_already_scaled=True),
                issues=issues,
                meter_key_policy="legacy",
            )
        )
        == []
    )
    assert issues[0]["reason"] == "missing meter mapping key"


def test_long_mdms_resolves_customer_and_applies_semantics_once():
    options = SourceOptions(
        values_already_scaled=False,
        multiplier=10,
        unit="kW",
        measurement_kind="interval_average_power",
        timestamp_convention="end",
    )
    result = list(
        canonicalize(
            [{"meter_id": "M01", "timestamp": "2024-03-01T00:00", "value": "4"}],
            sample_catalog(),
            options,
            source_id="abc",
        )
    )
    assert result[0].customer_id == "000123"
    assert result[0].start == datetime(2024, 2, 29, 23, 30)
    assert result[0].energy_kwh == 20
    assert result[0].source_id == "abc"


def test_wide_daily_rows_produce_48_intervals_and_keep_missing_values():
    row = {
        "meter_id": "M01",
        "date": "2024-02-01",
        **{f"slot_{i:02}": "1" for i in range(1, 49)},
    }
    row["slot_02"] = ""
    intervals = list(
        canonicalize(
            [row],
            sample_catalog(),
            SourceOptions(values_already_scaled=True, layout="wide"),
        )
    )
    assert len(intervals) == 48
    assert intervals[0].energy_kwh == 1
    assert intervals[1].energy_kwh is None
    assert intervals[-1].start.hour == 23


def test_invalid_rows_can_be_quarantined_with_provenance():
    issues = []
    rows = [
        {
            "meter_id": "missing",
            "timestamp": "2024-02-01T00:00",
            "value": "5",
            "_source_row": 7,
        }
    ]
    assert (
        list(
            canonicalize(
                rows,
                sample_catalog(),
                SourceOptions(values_already_scaled=True),
                issues=issues,
            )
        )
        == []
    )
    assert issues[0]["source_row"] == 7
    assert "mapping" in issues[0]["reason"]


def test_mismatched_scope_channel_and_nonfinite_values_are_rejected():
    base = {"meter_id": "M01", "timestamp": "2024-02-01T00:00", "value": "1"}
    for changes in (
        {"channel": "export"},
        {"organization_code": "other"},
        {"value": "nan"},
        {"customer_id": "wrong"},
    ):
        with pytest.raises(ValueError):
            list(
                canonicalize(
                    [{**base, **changes}],
                    sample_catalog(),
                    SourceOptions(values_already_scaled=True),
                )
            )


@pytest.mark.parametrize(
    "extra",
    [{"unit": "MWh"}, {"direction": "export"}, {"interval_end": "2024-02-01T01:00"}],
)
def test_row_semantics_cannot_contradict_source_declaration(extra):
    row = {
        "meter_id": "M01",
        "interval_start": "2024-02-01T00:00",
        "value": "1",
        **extra,
    }
    with pytest.raises(ValueError):
        list(
            canonicalize(
                [row], sample_catalog(), SourceOptions(values_already_scaled=True)
            )
        )


def test_invalid_wide_row_is_quarantined_atomically():
    row = {
        "meter_id": "M01",
        "date": "2024-02-01",
        **{f"slot_{i:02}": "1" for i in range(1, 49)},
    }
    row["slot_02"] = "-1"
    issues = []
    result = list(
        canonicalize(
            [row],
            sample_catalog(),
            SourceOptions(values_already_scaled=True, layout="wide"),
            issues=issues,
        )
    )
    assert result == []
    assert issues[0]["source_slot"] == 2
