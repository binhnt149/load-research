import pytest

from load_research.domain.strata import classify_annual_energy


@pytest.mark.parametrize(
    ("kwh", "expected"),
    [
        (0, None),
        (500, None),
        (501, "A"),
        (9999.99, "A"),
        (10000, "B"),
        (100000, "C"),
        (1000000, "D"),
        (10000000, "E"),
        (20000000, "E"),
    ],
)
def test_boundaries_can_belong_to_higher_group(kwh, expected):
    assert classify_annual_energy(kwh, boundary="higher") == expected


@pytest.mark.parametrize(
    ("kwh", "expected"),
    [(10000, "A"), (100000, "B"), (1000000, "C"), (10000000, "D")],
)
def test_boundaries_can_belong_to_lower_group(kwh, expected):
    assert classify_annual_energy(kwh, boundary="lower") == expected


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_annual_energy_cannot_be_classified(value):
    with pytest.raises(ValueError):
        classify_annual_energy(value, boundary="higher")


def test_boundary_policy_must_be_explicit():
    with pytest.raises(ValueError):
        classify_annual_energy(20000, boundary="unknown")
