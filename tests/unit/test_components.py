import pytest

from load_research.components import parse_components


def row(code="001", component="CN", name="Công nghiệp"):
    return {
        "Mã ngành nghề": code,
        "Tên ngành nghề": "Cơ khí " + code,
        "Mã thành phần": component,
        "Tên thành phần phụ tải": name,
    }


def test_catalog_preserves_codes_deduplicates_and_groups_industries():
    catalog = parse_components([row(), row(), row("002")])
    assert len(catalog) == 2
    assert catalog[0]["industry_code"] == "001"
    assert {r["component_code"] for r in catalog} == {"CN"}


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [row("")],
        [row(), row(component="DV")],
        [row(), row("002", name="Tên khác")],
        [row(), {**row(), "Tên ngành nghề": "Khác"}],
    ],
)
def test_invalid_or_conflicting_component_catalog_is_rejected(rows):
    with pytest.raises(ValueError):
        parse_components(rows)


def test_canonical_headers_are_also_supported():
    assert (
        parse_components(
            [
                {
                    "industry_code": "001",
                    "industry_name": "Cơ khí",
                    "component_code": "CN",
                    "component_name": "Công nghiệp",
                }
            ]
        )[0]["industry_name"]
        == "Cơ khí"
    )


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_component_template_uses_real_reader_and_keeps_leading_zero(
    tmp_path, extension
):
    from load_research.importers.tables import read_rows
    from load_research.input_templates import write_template

    path = write_template("components", tmp_path / f"components.{extension}")
    rows = parse_components(read_rows(path))
    assert rows[0]["industry_code"] == "001"
    assert rows[0]["component_name"] == "Công nghiệp"
