"""Figures rendered from computed curves, shared by desktop and reports."""

import hashlib
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from load_research.exports import cluster_display_name, convert_curve


def build_figure(
    cell: dict,
    day_type: str,
    source_minutes: int,
    *,
    target_minutes: int | None = None,
    unit: str = "kW",
    scope: str = "industry_scaled",
    normalization: str | None = None,
    components: bool = True,
    stacked: bool = False,
    cluster_ids: tuple[str, ...] = (),
    run_id: str = "",
    figure: Figure | None = None,
) -> Figure:
    target_minutes = target_minutes or source_minutes
    source_key = "energy" if scope == "industry_scaled" else "sample"
    component_key = (
        "contributions" if scope == "industry_scaled" else "sample_contributions"
    )
    if normalization:
        source_key, component_key = "sample", "sample_contributions"
    figure = figure if figure is not None else Figure(figsize=(10, 4.8))
    figure.clear()
    figure.set_layout_engine("constrained")
    axes = figure.add_subplot(111)
    computed = cell["result"]
    values = computed[source_key].get(day_type)
    hours = np.arange(1440 // target_minutes) * target_minutes / 60
    vector = (
        None
        if values is None
        else convert_curve(values, source_minutes, target_minutes, unit, normalization)
    )
    if vector is None:
        axes.text(
            0.5,
            0.5,
            "Không có đường cong hợp lệ cho lựa chọn này",
            ha="center",
            transform=axes.transAxes,
        )
    else:
        axes.plot(hours, vector, color="#123B39", linewidth=2.6, label="Chung")
        group_values, labels = [], []
        for index, (label, component) in enumerate(
            sorted(computed[component_key].get(day_type, {}).items())
        ):
            if cluster_ids and label not in cluster_ids:
                continue
            curve = convert_curve(
                component, source_minutes, target_minutes, unit, normalization
            )
            if curve is not None and components:
                display = (
                    cell.get("cluster_names", {})
                    .get(day_type, {})
                    .get(label, cluster_display_name(label))
                )
                labels.append(display)
                group_values.append(curve)
                if not stacked or normalization:
                    axes.plot(
                        hours,
                        curve,
                        linewidth=1.5,
                        linestyle=("--", ":", "-.")[index % 3],
                        label=display,
                    )
        if stacked and group_values and normalization is None:
            axes.stackplot(hours, *group_values, labels=labels, alpha=0.65)
        legend = axes.legend(loc="best", fontsize=8)
        for text in legend.get_texts():
            text.set_parse_math(False)
    label = (
        f"Chuẩn hoá ({normalization})"
        if normalization
        else f"Công suất trung bình ({unit})"
        if unit == "kW"
        else "Điện năng chu kỳ (kWh)"
    )
    axes.set(xlabel="Giờ trong ngày", ylabel=label, xlim=(0, 24))
    axes.set_ylim(bottom=0)
    axes.set_xticks(range(0, 25, 2))
    axes.grid(alpha=0.2)
    display_scope = (
        "Hình dạng tập mẫu"
        if normalization
        else "Suy rộng toàn ngành"
        if scope == "industry_scaled"
        else "Tổng hợp tập mẫu"
    )
    display_day = {
        "weekday": "Ngày thường",
        "saturday": "Thứ Bảy",
        "sunday": "Chủ nhật",
        "holiday": "Lễ",
    }.get(day_type, day_type)
    figure.suptitle(
        f"{cell['industry_code']} · {cell['year_month']} · {display_day}\n{display_scope} · {computed['status']} · run {run_id[:12]}",
        fontsize=11,
        parse_math=False,
    )
    return figure


def export_charts(
    result: dict,
    directory: Path,
    *,
    formats: tuple[str, ...] = ("png",),
    day_types: tuple[str, ...] = (),
    check: Callable[[], None] = lambda: None,
    **options,
) -> list[Path]:
    if not formats or any(format_name not in ("png", "svg") for format_name in formats):
        raise ValueError("chart formats must be PNG/SVG")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, cell in enumerate(result["cells"], 1):
        key = (
            "sample"
            if options.get("normalization")
            or options.get("scope") == "sample_portfolio"
            else "energy"
        )
        for kind in cell["result"][key]:
            check()
            if day_types and kind not in day_types:
                continue
            digest = hashlib.sha256(
                f"{cell['industry_code']}:{cell['year_month']}:{kind}".encode()
            ).hexdigest()[:12]
            figure = build_figure(
                cell,
                kind,
                result["config"]["interval_minutes"],
                run_id=result["run_id"],
                **options,
            )
            for format_name in formats:
                destination = directory / f"{index:04}-{digest}.{format_name}"
                if destination.exists():
                    raise FileExistsError("chart destination already exists")
                descriptor, name = tempfile.mkstemp(prefix=".chart-", dir=directory)
                os.close(descriptor)
                try:
                    figure.savefig(name, format=format_name, dpi=150)
                    os.link(name, destination)
                finally:
                    Path(name).unlink(missing_ok=True)
                paths.append(destination)
            figure.clear()
    return paths
