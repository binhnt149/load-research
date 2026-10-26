"""A selected view is the single numerical source for charts, tables and exports."""

import csv
import json
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

import numpy as np
import xlsxwriter
from matplotlib.figure import Figure

from load_research.error_messages import import_issue_rows
from load_research.exports import _portable_request, safe_csv_text
from load_research.presentation import DAY_TYPES, field_label, translated_value
from load_research.workspace import file_hash

KINDS = {
    "overall": "Tổng hợp",
    "industry": "So sánh ngành",
    "day_type": "So sánh loại ngày",
    "behavior": "Đóng góp nhóm hành vi",
    "source": "Mẫu nguồn trước VEE",
    "processed": "Mẫu sau VEE",
    "expanded": "Phụ tải suy rộng",
}
METHODS = {
    "representative": "Biểu đồ đại diện theo loại ngày",
    "variation": "Giữ biến thiên ngày, hệ số tháng riêng",
}


def interval_records(view: dict) -> list[dict]:
    rows = []
    for index in range(1440 // view["interval_minutes"]):
        start, end = (
            index * view["interval_minutes"],
            (index + 1) * view["interval_minutes"],
        )
        row = {
            "Chu kỳ": index + 1,
            "Bắt đầu": f"{start // 60:02}:{start % 60:02}",
            "Kết thúc": f"{end // 60:02}:{end % 60:02}",
        }
        for curve in view["series"]:
            label = (
                "Chung"
                if curve["kind"] == "overall"
                else f"{KINDS[curve['kind']]} · {curve['label']}"
            )
            row[label] = None if curve["values"] is None else curve["values"][index]
        rows.append(row)
    return rows


def render_view(
    view: dict,
    *,
    figure: Figure | None = None,
    families: tuple[str, ...] = (
        "industry",
        "day_type",
        "behavior",
        "source",
        "processed",
        "expanded",
    ),
    stacked: bool = False,
) -> Figure:
    figure = figure if figure is not None else Figure(figsize=(10, 4.8))
    figure.clear()
    figure.set_layout_engine("constrained")
    axes = figure.add_subplot(111)
    hours = np.arange(1440 // view["interval_minutes"]) * view["interval_minutes"] / 60
    curves = sorted(view["series"], key=lambda row: row["kind"] != "overall")
    for curve in curves:
        if curve["values"] is None or (
            curve["kind"] != "overall" and curve["kind"] not in families
        ):
            continue
        values = np.asarray(curve["values"], dtype=float)
        if stacked and not view["normalization"] and curve["kind"] == "behavior":
            continue
        axes.plot(
            hours,
            values,
            label=curve["label"],
            linewidth=2.5 if curve["kind"] == "overall" else 1.2,
            linestyle="-" if curve["kind"] == "overall" else "--",
            picker=5,
        )
    contributions = [
        curve
        for curve in curves
        if curve["kind"] == "behavior" and curve["values"] is not None
    ]
    if (
        stacked
        and not view["normalization"]
        and "behavior" in families
        and contributions
    ):
        axes.stackplot(hours, *[row["values"] for row in contributions], alpha=0.5)
    if not view["complete"]:
        axes.text(
            0.02,
            0.95,
            "Chưa đủ dữ liệu để tổng hợp toàn bộ lựa chọn",
            transform=axes.transAxes,
            va="top",
            fontsize=9,
        )
    if axes.lines:
        handles, labels = axes.get_legend_handles_labels()
        legend = axes.legend(
            handles[:8],
            [" ".join(label.split())[:70] for label in labels[:8]],
            loc="upper right",
            fontsize=7,
            ncols=2,
        )
        if len(handles) > 8:
            axes.text(
                0.01,
                0.02,
                "Chú giải: 8 đường đầu; xem đầy đủ trong bảng chu kỳ.",
                transform=axes.transAxes,
                fontsize=7,
            )
        for text in legend.get_texts():
            text.set_parse_math(False)
    ylabel = (
        "Chuẩn hóa\n(p.u.)"
        if view["normalization"]
        else "Công suất\ntrung bình (kW)"
        if view["unit"] == "kW"
        else "Điện năng\nchu kỳ (kWh)"
    )
    axes.set(xlabel="Giờ trong ngày", ylabel=ylabel, xlim=(0, 24))
    axes.set_xticks(range(0, 25, 2))
    axes.set_ylim(bottom=0)
    axes.grid(alpha=0.2)
    codes = ",".join(view["industry_codes"][:3])
    if len(view["industry_codes"]) > 3:
        codes += f"… ({len(view['industry_codes'])} ngành)"
    industries = "Toàn đơn vị" if view["level"] == "organization" else "Ngành " + codes
    kinds = "/".join(DAY_TYPES[kind] for kind in view["day_types"])
    scope = translated_value("profile_scope", view["scope"])
    normalization = {
        None: "",
        "mean": " · TB=1",
        "share": " · Tổng=1",
        "peak": " · Đỉnh=1",
    }[view["normalization"]]
    quality = (
        "Chưa đủ dữ liệu"
        if not view["complete"]
        else "Có cảnh báo / cần kiểm tra"
        if set(view["quality_statuses"]) != {"valid"}
        else "Hợp lệ"
    )
    method = {
        "representative": "Đại diện theo loại ngày",
        "variation": "Giữ biến thiên ngày",
    }.get(view.get("method"), f"{view['day_count']} ngày theo lịch")
    organization = " ".join(view["organization_scope"].split())[:32]
    figure.suptitle(
        f"{organization} · {view.get('date', view['year_month'])} · {industries} · {kinds}\n"
        f"{scope}{normalization} · {method} · {quality} · lần {view['run_id'][:8]}",
        fontsize=10,
        parse_math=False,
    )
    return figure


def _curve_metadata(view: dict, curve: dict) -> dict:
    return {
        "Mã lần nghiên cứu": view["run_id"],
        "Phạm vi đơn vị": view["organization_scope"],
        "Tháng": view["year_month"],
        "Ngày": view.get("date", ""),
        "Phương pháp theo ngày": METHODS.get(
            view.get("method", ""), "Đại diện theo loại ngày"
        ),
        "Phạm vi ngành": ", ".join(view["industry_codes"]),
        "Phạm vi phụ tải": translated_value("profile_scope", view["scope"]),
        "Các loại ngày đã chọn": ", ".join(
            DAY_TYPES[kind] for kind in view["day_types"]
        ),
        "Chuẩn hóa": {
            None: "Giá trị vật lý",
            "mean": "Trung bình bằng 1",
            "share": "Tổng bằng 1",
            "peak": "Đỉnh bằng 1",
        }[view["normalization"]],
        "Mã đường": curve["id"],
        "Loại đường biểu diễn": KINDS[curve["kind"]],
        "Tên đường": curve["label"],
    }


def report_rows(view: dict, layout: str = "long") -> Iterator[dict]:
    for curve in view["series"]:
        metadata = _curve_metadata(view, curve)
        values = curve["values"]
        if layout == "wide":
            yield {
                **metadata,
                "Độ dài chu kỳ (phút)": view["interval_minutes"],
                "Đơn vị": view["unit"],
                "Đủ dữ liệu tổng hợp": "Có" if view["complete"] else "Không",
                **{
                    f"Chu kỳ {index + 1:02}": None if values is None else values[index]
                    for index in range(1440 // view["interval_minutes"])
                },
            }
        else:
            for index in range(1440 // view["interval_minutes"]):
                yield {
                    **metadata,
                    "Chu kỳ": index + 1,
                    "Phút bắt đầu": index * view["interval_minutes"],
                    "Độ dài chu kỳ (phút)": view["interval_minutes"],
                    "Đơn vị": view["unit"],
                    "Giá trị": None if values is None else values[index],
                    "Đủ dữ liệu tổng hợp": "Có" if view["complete"] else "Không",
                }


def export_views(
    result: dict,
    views: list[dict],
    destination: Path,
    *,
    include_xlsx: bool = True,
    layout: str = "long",
    include_members: bool = False,
    chart_formats: tuple[str, ...] = (),
    check: Callable[[], None] = lambda: None,
) -> Path:
    check()
    if layout not in ("long", "wide"):
        raise ValueError("invalid output layout")
    if not views:
        raise ValueError("no industry-month cells match the export selection")
    if any(value not in ("png", "svg") for value in chart_formats):
        raise ValueError("chart formats must be PNG/SVG")
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("export destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".load-research-report-", dir=destination.parent
    ) as temporary:
        staging = Path(temporary)
        workbook = (
            xlsxwriter.Workbook(
                staging / "profiles.xlsx",
                {
                    "constant_memory": True,
                    "strings_to_formulas": False,
                    "strings_to_urls": False,
                },
            )
            if include_xlsx
            else None
        )
        try:
            sheet = workbook.add_worksheet("Biểu đồ phụ tải") if workbook else None
            columns = list(next(report_rows(views[0], layout)))
            if sheet:
                sheet.write_row(0, 0, columns)
                sheet.freeze_panes(1, 0)
            with (staging / "profiles.csv").open(
                "x", encoding="utf-8-sig", newline=""
            ) as stream:
                writer = csv.writer(stream)
                writer.writerow(columns)
                for index, row in enumerate(
                    (row for view in views for row in report_rows(view, layout)), 1
                ):
                    if index % 256 == 1:
                        check()
                    if workbook and index >= 1_048_576:
                        raise ValueError(
                            "Excel row limit would be exceeded; select CSV-only export or a smaller scope"
                        )
                    values = list(row.values())
                    writer.writerow([safe_csv_text(value) for value in values])
                    if sheet:
                        sheet.write_row(index, 0, values)
            if workbook:
                for name, rows in (
                    (
                        "Hệ số và cân bằng",
                        [row for view in views for row in view["factors"]],
                    ),
                    ("Chất lượng tháng", result.get("quality", [])),
                    (
                        "Suy rộng từng ngày",
                        [
                            {
                                "date": view.get("date"),
                                "method": view.get("method"),
                                **row,
                            }
                            for view in views
                            for row in view.get("daily_factors", [])
                        ],
                    ),
                ):
                    table = workbook.add_worksheet(name)
                    fields = sorted(
                        {
                            key
                            for row in rows
                            for key, value in row.items()
                            if not isinstance(value, (dict, list))
                        }
                    )
                    table.write_row(0, 0, [field_label(key) for key in fields])
                    for index, row in enumerate(rows, 1):
                        table.write_row(
                            index,
                            0,
                            [translated_value(key, row.get(key)) for key in fields],
                        )
        finally:
            if workbook:
                workbook.close()
        if include_members:
            codes = {code for view in views for code in view["industry_codes"]}
            periods = {view["year_month"] for view in views}
            members = [
                {
                    "industry_code": cell["industry_code"],
                    "year_month": cell["year_month"],
                    **member,
                }
                for cell in result["cells"]
                if cell["industry_code"] in codes and cell["year_month"] in periods
                for member in cell["members"]
                if any(
                    cell["industry_code"] in view["industry_codes"]
                    and cell["year_month"] == view["year_month"]
                    and member["day_type"] in view["day_types"]
                    and (
                        not view.get("cluster_ids")
                        or member["cluster_id"] in view["cluster_ids"]
                    )
                    for view in views
                )
            ]
            if members:
                with (staging / "cluster-members.csv").open(
                    "x", encoding="utf-8-sig", newline=""
                ) as stream:
                    writer = csv.writer(stream)
                    fields = list(members[0])
                    writer.writerow([field_label(key) for key in fields])
                    for row in members:
                        check()
                        writer.writerow(
                            [
                                safe_csv_text(translated_value(key, row.get(key)))
                                for key in fields
                            ]
                        )
        for index, view in enumerate(views):
            check()
            if chart_formats:
                (staging / "charts").mkdir(exist_ok=True)
                figure = render_view(view)
                for format_name in chart_formats:
                    figure.savefig(
                        staging / "charts" / f"{index + 1:04}.{format_name}",
                        format=format_name,
                        dpi=150,
                    )
                figure.clear()
        write_summary_csv(
            staging / "import-issues.csv", import_issue_rows(result), check
        )
        write_summary_csv(
            staging / "quality-summary.csv",
            [
                row
                for row in result.get("quality", [])
                if row["period"] in {view["year_month"] for view in views}
            ],
            check,
        )
        write_summary_csv(
            staging / "balance-checks.csv",
            [
                {"year_month": view["year_month"], **row}
                for view in views
                for row in view["factors"]
            ],
            check,
        )
        write_summary_csv(
            staging / "daily-factors.csv",
            [
                {"date": view.get("date"), "method": view.get("method"), **row}
                for view in views
                for row in view.get("daily_factors", [])
            ],
            check,
        )
        from load_research.methodology import CALCULATIONS

        (staging / "phuong-phap.md").write_text(CALCULATIONS, encoding="utf-8")
        (staging / "run-config.json").write_text(
            json.dumps(
                _portable_request(result), ensure_ascii=False, allow_nan=False, indent=2
            ),
            encoding="utf-8",
        )
        manifest = {
            "run_id": result["run_id"],
            "config": result.get("config", {}),
            "calendar": result.get("calendar", {}),
            "method_version": result.get("method_version"),
            "software": result.get("software", {}),
            "sources": [
                {
                    "name": str(source["path"]).replace("\\", "/").rsplit("/", 1)[-1],
                    "sha256": source["sha256"],
                }
                for source in result.get("sources", [])
            ],
            "views": [
                {key: value for key, value in view.items() if key != "series"}
                for view in views
            ],
            "files": [
                {"name": str(path.relative_to(staging)), "sha256": file_hash(path)}
                for path in sorted(staging.rglob("*"))
                if path.is_file()
            ],
        }
        (staging / "export-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2),
            encoding="utf-8",
        )
        check()
        if destination.exists():
            raise FileExistsError("export destination already exists")
        os.rename(staging, destination)
    return destination


def write_summary_csv(path: Path, rows: list[dict], check: Callable[[], None]) -> None:
    fields = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if not isinstance(value, (dict, list))
        }
    )
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([field_label(key) for key in fields] or ["Không có dữ liệu"])
        for row in rows:
            check()
            writer.writerow(
                [
                    safe_csv_text(translated_value(key, row.get(key)))
                    if not isinstance(row.get(key), (dict, list))
                    else ""
                    for key in fields
                ]
            )
