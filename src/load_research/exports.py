"""Atomic report bundles with explicit units, status and safe spreadsheet text."""

import csv
import json
import os
import tempfile
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import numpy as np
import xlsxwriter

from load_research.domain.energy import convert_curve, resample_energy
from load_research.workspace import file_hash

EXCEL_MAX_ROWS = 1_048_576
META_COLUMNS = [
    "run_id",
    "organization_scope",
    "industry_code",
    "industry_name",
    "year_month",
    "day_type",
    "profile_scope",
    "profile_kind",
    "cluster_id",
    "cluster_name",
    "interval_minutes",
    "unit",
    "result_status",
]


def apply_annotations(result: dict, annotations: list[dict]) -> dict:
    cells = []
    for cell in result["cells"]:
        names: dict = {}
        for annotation in annotations:
            if (
                annotation["industry_code"] == cell["industry_code"]
                and annotation["year_month"] == cell["year_month"]
            ):
                names.setdefault(annotation["day_type"], {})[
                    annotation["cluster_id"]
                ] = annotation["label"]
        cells.append({**cell, "cluster_names": names})
    return {**result, "cells": cells, "cluster_annotations": annotations}


def safe_csv_text(value: object) -> object:
    if isinstance(value, str) and (
        value[:1] in ("\t", "\r", "\n") or value.lstrip()[:1] in ("=", "+", "-", "@")
    ):
        return "'" + value
    return value


def source_basename(path: str) -> str:
    """Interpret saved paths from either supported OS, regardless of host OS."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def cluster_display_name(label: str) -> str:
    if label.startswith("group_"):
        return "Nhóm " + label.removeprefix("group_")
    return {
        "inactive": "Không hoạt động",
        "unclassified": "Chưa phân loại",
        "not_segmented": "Chưa phân nhóm",
    }.get(label, label)


def curve_rows(
    result: dict,
    *,
    interval_minutes: int,
    unit: str,
    scope: str,
    normalization: str | None,
    day_types: tuple[str, ...] = (),
    cluster_ids: tuple[str, ...] = (),
) -> Iterator[tuple[dict, np.ndarray]]:
    source_minutes = result["config"]["interval_minutes"]
    overall_key = (
        "energy" if scope == "industry_scaled" and normalization is None else "sample"
    )
    contribution_key = (
        "contributions" if overall_key == "energy" else "sample_contributions"
    )
    for cell in result["cells"]:
        computed = cell["result"]
        for kind, values in computed[overall_key].items():
            if day_types and kind not in day_types:
                continue
            base = dict(
                zip(
                    META_COLUMNS,
                    [
                        result["run_id"],
                        result["config"]["scope"],
                        cell["industry_code"],
                        cell.get("industry_name", ""),
                        cell["year_month"],
                        kind,
                        "sample_portfolio" if normalization else scope,
                        "overall",
                        "",
                        "",
                        interval_minutes,
                        ("share" if normalization == "share" else "p.u.")
                        if normalization
                        else unit,
                        computed["status"],
                    ],
                    strict=True,
                )
            )
            vector = convert_curve(
                values, source_minutes, interval_minutes, unit, normalization
            )
            if vector is not None:
                yield (
                    {
                        **base,
                        "profile_kind": "normalized_shape"
                        if normalization
                        else "overall",
                    },
                    vector,
                )
            for label, component in computed[contribution_key].get(kind, {}).items():
                if cluster_ids and label not in cluster_ids:
                    continue
                vector = convert_curve(
                    component, source_minutes, interval_minutes, unit, normalization
                )
                if vector is not None:
                    yield (
                        {
                            **base,
                            "profile_kind": "normalized_shape"
                            if normalization
                            else "cluster_contribution",
                            "cluster_id": label,
                            "cluster_name": cell.get("cluster_names", {})
                            .get(kind, {})
                            .get(label, cluster_display_name(label)),
                        },
                        vector,
                    )


def _tabular_rows(
    curves: Iterable[tuple[dict, np.ndarray]], layout: str
) -> Iterator[dict]:
    for metadata, vector in curves:
        if layout == "wide":
            yield {
                **metadata,
                **{
                    f"slot_{index:02}": float(value)
                    for index, value in enumerate(vector, 1)
                },
            }
        else:
            minutes = metadata["interval_minutes"]
            for index, value in enumerate(vector):
                start, end = index * minutes, (index + 1) * minutes
                yield {
                    **metadata,
                    "slot_index": index + 1,
                    "start_time": f"{start // 60:02}:{start % 60:02}",
                    "end_time": f"{end // 60:02}:{end % 60:02}",
                    "value": float(value),
                }


def _csv(
    path: Path,
    columns: list[str],
    rows: Iterable[dict],
    check: Callable[[], None] = lambda: None,
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            check()
            writer.writerow(
                {column: safe_csv_text(row.get(column, "")) for column in columns}
            )


def _columns(rows: list[dict], fallback: str) -> list[str]:
    return list(dict.fromkeys(key for row in rows for key in row)) or [fallback]


def _xlsx(
    path: Path,
    columns: list[str],
    curves,
    layout: str,
    result: dict,
    quality: list[dict],
    balance: list[dict],
    check: Callable[[], None],
) -> None:
    with xlsxwriter.Workbook(
        path,
        {
            "constant_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        },
    ) as workbook:
        header = workbook.add_format({"bold": True, "bg_color": "#DCEEEA"})

        def sheet(name: str, headings: list[str], items: Iterable[dict]) -> None:
            worksheet = workbook.add_worksheet(name)
            worksheet.freeze_panes(1, 0)
            worksheet.write_row(0, 0, headings, header)
            index = 0
            for index, row in enumerate(items, 1):
                check()
                worksheet.write_row(index, 0, [row.get(key, "") for key in headings])
            worksheet.set_column(0, len(headings) - 1, 18)
            if index:
                worksheet.autofilter(0, 0, index, len(headings) - 1)

        sheet(
            "Readme",
            ["field", "value"],
            [
                {"field": "run_id", "value": result["run_id"]},
                {"field": "status", "value": result["status"]},
                {"field": "method", "value": result["method_version"]},
                {
                    "field": "interpretation",
                    "value": "Representative day profiles; not actual daily MDMS readings",
                },
            ],
        )
        sheet(
            "Profiles",
            columns,
            _tabular_rows(
                (curve for curve in curves if not curve[0]["cluster_id"]), layout
            ),
        )
        sheet(
            "Cluster_Contributions",
            columns,
            _tabular_rows(
                (curve for curve in curves if curve[0]["cluster_id"]), layout
            ),
        )
        sheet("Quality", _columns(quality, "period"), quality)
        sheet(
            "Balance_Checks",
            list(balance[0]) if balance else ["industry_code"],
            balance,
        )
        sheet(
            "Parameters",
            ["parameter", "value"],
            [
                {"parameter": key, "value": json.dumps(value, ensure_ascii=False)}
                for key, value in result["config"].items()
            ],
        )


def _methodology(result: dict) -> str:
    return f"""# Phương pháp nghiên cứu phụ tải

Run: {result["run_id"]}; trạng thái: {result["status"]}; phương pháp: {result["method_version"]}.

Đây là đường cong ngày đại diện theo ngành, năm-tháng và loại ngày. Điện năng là kWh trong từng chu kỳ; kW là công suất trung bình chu kỳ. Chuẩn hoá là đại lượng không thứ nguyên.

Trung bình từng khách hàng trước khi tổng hợp, dùng cùng tập khách hàng đủ điều kiện giữa các loại ngày. Giữ ngày 0 hợp lệ; bù khoảng trống có giới hạn và lưu nhật ký, không bù cả ngày tự động. Phân cụm hình dạng đã chuẩn hoá; giữ nhóm không hoạt động/chưa phân loại trong tổng đóng góp.

`F[t,k] = sum_i(w[i] * M[i,t,k])`; `S = sum_t(N[t] * sum_k(F[t,k]))`; `alpha = A/S`; `E[t,k] = alpha * F[t,k]`; `P[t,k] = E[t,k]/delta_t`.

Tổng điện năng theo lịch tháng bằng A, và các đóng góp nhóm cộng thành đường cong chung. Chuyển 48 → 24 chu kỳ bằng cộng kWh, không cộng trực tiếp kW. Mỗi nhóm hành vi có dạng chuẩn hoá riêng; các đường đã chuẩn hoá độc lập không phải các thành phần vật lý để cộng.

Số tháng thương phẩm phải được diễn giải theo `billing_basis` của từng ô. Khớp tổng A không chứng minh hình dạng mẫu đại diện toàn tổng thể. Hồ sơ thiết kế mẫu chưa được xác minh; không tuyên bố độ tin cậy hoặc sai số suy luận toàn tổng thể.

Nguồn/checksum nằm trong manifest; cấu hình đầy đủ ở run-config.json; chất lượng, ô thiếu và kiểm tra cân bằng đi kèm. Số liệu giữ độ chính xác tính toán, làm tròn khi đưa vào báo cáo.

## Tham số đã sử dụng

```json
{json.dumps(result["config"], ensure_ascii=False, indent=2)}
```

Lịch hiệu lực và ngữ nghĩa nhập (kênh, hệ số, dấu thời gian, ánh xạ) được giữ trong `run-config.json`.
Các đường dẫn nguồn được rút về tên tệp; cần đặt lại đường dẫn khi tái chạy trên máy khác và đối chiếu checksum trong manifest.
"""


def _portable_request(result: dict) -> dict:
    payload = {
        **result.get("request", {"config": result["config"]}),
        "calendar": result.get("calendar", {}),
    }
    for key in ("cmis_paths", "billing_paths", "calendar_paths"):
        payload[key] = [source_basename(name) for name in payload.get(key, [])]
    payload["mdms_sources"] = [
        {**source, "path": source_basename(source["path"])}
        for source in payload.get("mdms_sources", [])
    ]
    return payload


def export_study(
    result: dict,
    destination: Path,
    *,
    interval_minutes: int | None = None,
    unit: str = "kW",
    layout: str = "wide",
    scope: str = "industry_scaled",
    normalization: str | None = None,
    include_members: bool = False,
    include_xlsx: bool = True,
    chart_formats: tuple[str, ...] = (),
    industry_codes: tuple[str, ...] = (),
    periods: tuple[str, ...] = (),
    day_types: tuple[str, ...] = (),
    cluster_ids: tuple[str, ...] = (),
    cancelled: Callable[[], bool] = lambda: False,
) -> Path:
    def check() -> None:
        if cancelled():
            from load_research.application.pipeline import ResearchCancelled

            raise ResearchCancelled("export cancelled")

    check()
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("export destination already exists")
    interval_minutes = interval_minutes or result["config"]["interval_minutes"]
    if (
        interval_minutes not in (30, 60)
        or layout not in ("long", "wide")
        or scope not in ("industry_scaled", "sample_portfolio")
    ):
        raise ValueError("invalid output resolution/layout/scope")
    resample_energy(
        np.zeros(1440 // result["config"]["interval_minutes"]),
        result["config"]["interval_minutes"],
        interval_minutes,
    )
    if unit not in ("kW", "kWh") or normalization not in (
        None,
        "share",
        "mean",
        "peak",
    ):
        raise ValueError("invalid output unit or normalization")
    cells = [
        cell
        for cell in result["cells"]
        if (not industry_codes or cell["industry_code"] in industry_codes)
        and (not periods or cell["year_month"] in periods)
    ]
    if not cells:
        raise ValueError("no industry-month cells match the export selection")
    result = {
        **result,
        "cells": cells,
        "quality": [
            row
            for row in result.get("quality", [])
            if not periods or row["period"] in periods
        ],
    }
    curves = list(
        curve_rows(
            result,
            interval_minutes=interval_minutes,
            unit=unit,
            scope=scope,
            normalization=normalization,
            day_types=day_types,
            cluster_ids=cluster_ids,
        )
    )
    expected_rows = len(curves) * (1440 // interval_minutes if layout == "long" else 1)
    if include_xlsx and expected_rows + 1 > EXCEL_MAX_ROWS:
        raise ValueError(
            "Excel row limit would be exceeded; select CSV-only export or a smaller scope"
        )
    columns = META_COLUMNS + (
        [f"slot_{index:02}" for index in range(1, 1440 // interval_minutes + 1)]
        if layout == "wide"
        else ["slot_index", "start_time", "end_time", "value"]
    )
    quality = [
        {
            key: value
            for key, value in entry.items()
            if isinstance(value, (int, float, str))
        }
        for entry in result.get("quality", [])
    ]
    balance = [
        {
            "industry_code": cell["industry_code"],
            "year_month": cell["year_month"],
            "status": cell["result"]["status"],
            "billing_basis": cell["billing_basis"],
            "billing_kwh": cell["result"]["billing_kwh"],
            "background_kwh": cell["result"]["background_kwh"],
            "alpha": cell["result"]["alpha"],
            "balance_error_kwh": cell["result"]["diagnostics"].get("balance_error_kwh"),
        }
        for cell in result["cells"]
    ]
    cluster_summary = [
        {
            "industry_code": cell["industry_code"],
            "year_month": cell["year_month"],
            "day_type": kind,
            "cluster_id": label,
            **statistics,
        }
        for cell in cells
        for kind, groups in cell["result"]["diagnostics"]
        .get("cluster_statistics", {})
        .items()
        for label, statistics in groups.items()
        if (not day_types or kind in day_types)
        and (not cluster_ids or label in cluster_ids)
    ]
    excluded = [
        {"period": entry["period"], "reason": reason, "customer_count": count}
        for entry in result.get("quality", [])
        for reason, count in Counter(entry.get("excluded", {}).values()).items()
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".load-research-export-", dir=destination.parent
    ) as staging_name:
        staging = Path(staging_name)
        _csv(staging / "profiles.csv", columns, _tabular_rows(curves, layout), check)
        _csv(
            staging / "cluster-summary.csv",
            _columns(cluster_summary, "industry_code"),
            cluster_summary,
        )
        _csv(staging / "quality-summary.csv", _columns(quality, "period"), quality)
        _csv(
            staging / "excluded-data.csv",
            ["period", "reason", "customer_count"],
            excluded,
        )
        if include_xlsx:
            _xlsx(
                staging / "profiles.xlsx",
                columns,
                curves,
                layout,
                result,
                quality,
                balance,
                check,
            )
        if include_members:
            members = [
                {
                    "industry_code": cell["industry_code"],
                    "year_month": cell["year_month"],
                    **member,
                }
                for cell in result["cells"]
                for member in cell["members"]
                if (not day_types or member["day_type"] in day_types)
                and (not cluster_ids or member["cluster_id"] in cluster_ids)
            ]
            _csv(
                staging / "cluster-members.csv",
                list(members[0]) if members else ["customer_id"],
                members,
            )
        from load_research.methodology import CALCULATIONS

        (staging / "methodology.md").write_text(
            CALCULATIONS + "\n\n" + _methodology(result), encoding="utf-8"
        )
        (staging / "run-config.json").write_text(
            json.dumps(
                _portable_request(result), ensure_ascii=False, indent=2, allow_nan=False
            ),
            encoding="utf-8",
        )
        if chart_formats:
            from load_research.charts import export_charts

            export_charts(
                result,
                staging / "charts",
                formats=chart_formats,
                target_minutes=interval_minutes,
                unit=unit,
                scope=scope,
                normalization=normalization,
                day_types=day_types,
                cluster_ids=cluster_ids,
                check=check,
            )
        missing = [
            {
                "industry_code": cell["industry_code"],
                "year_month": cell["year_month"],
                "status": cell["result"]["status"],
            }
            for cell in result["cells"]
            if cell["result"]["status"] not in ("valid", "valid_with_warnings")
        ]
        manifest = {
            "schema_version": 1,
            "run_id": result["run_id"],
            "status": result["status"],
            "missing_or_preview_cells": missing,
            "scope": "sample_portfolio" if normalization else scope,
            "normalization": normalization,
            "unit": unit if normalization is None else "dimensionless",
            "filters": {
                "industry_codes": industry_codes,
                "periods": periods,
                "day_types": day_types,
                "cluster_ids": cluster_ids,
            },
            "quality_scope": "whole_month",
            "balance_check_scope": "original_full_month_model",
            "cluster_annotations": result.get("cluster_annotations", []),
            "interval_minutes": interval_minutes,
            "layout": layout,
            "method_version": result["method_version"],
            "software": result.get("software", {}),
            "sources": [
                {"name": source_basename(source["path"]), "sha256": source["sha256"]}
                for source in result.get("sources", [])
            ],
            "files": [
                {
                    "name": str(path.relative_to(staging)),
                    "sha256": file_hash(path),
                    "size": path.stat().st_size,
                }
                for path in sorted(staging.rglob("*"))
                if path.is_file()
            ],
        }
        (staging / "export-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        check()
        if destination.exists():
            raise FileExistsError("export destination was created by another operation")
        os.rename(staging, destination)
    return destination
