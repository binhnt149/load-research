"""One industry belongs to one declared load component, without double counting."""

from collections.abc import Iterable

from load_research.input_errors import source_row

HEADERS = {
    "industry_code": "Mã ngành nghề",
    "industry_name": "Tên ngành nghề",
    "component_code": "Mã thành phần",
    "component_name": "Tên thành phần phụ tải",
}


def parse_components(rows: Iterable[dict]) -> list[dict]:
    industries: dict[str, dict] = {}
    names: dict[str, str] = {}
    for source in rows:
        with source_row(source):
            row = {}
            for key, label in HEADERS.items():
                value = str(source.get(key, source.get(label, ""))).strip()
                if not value or len(value) > 256:
                    raise ValueError(f"Cột «{label}» bị trống hoặc dài quá 256 ký tự.")
                if (
                    key in source
                    and label in source
                    and str(source[label]).strip() != value
                ):
                    raise ValueError(
                        f"Hai cột của «{label}» có giá trị không thống nhất."
                    )
                row[key] = value
            code, component = row["industry_code"], row["component_code"]
            if code in industries and industries[code] != row:
                raise ValueError(
                    f"Mã ngành {code} có tên hoặc thành phần không thống nhất."
                )
            if component in names and names[component] != row["component_name"]:
                raise ValueError(f"Mã thành phần {component} có nhiều tên khác nhau.")
            industries[code] = row
            names[component] = row["component_name"]
    if not industries:
        raise ValueError("Danh mục thành phần phụ tải chưa có dòng dữ liệu.")
    return [industries[code] for code in sorted(industries)]


def apply_component_catalog(result: dict, catalog: dict | None) -> dict:
    if catalog is None:
        return result
    names = {row["industry_code"]: row["industry_name"] for row in catalog["rows"]}
    return {
        **result,
        "component_catalog": catalog,
        "cells": [
            {
                **cell,
                "industry_name": names.get(
                    cell["industry_code"], cell.get("industry_name", "")
                ),
            }
            for cell in result["cells"]
        ],
    }
