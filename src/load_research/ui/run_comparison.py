"""Render a matching saved run without coupling comparison rules to Qt controls."""

from load_research.exports import convert_curve
from load_research.presentation import field_label


def compare_runs(current, comparison, cell, kind, selection, figure, records) -> str:
    if not records or records[0].get("Chung") is None:
        return (
            "Lần hiện tại thiếu đường cong cho lựa chọn này; chưa thể tính chênh lệch."
        )
    other = next(
        (
            item
            for item in comparison["cells"]
            if item["industry_code"] == cell["industry_code"]
            and item["year_month"] == cell["year_month"]
        ),
        None,
    )
    changes = [
        name
        for name in sorted(set(current["config"]) | set(comparison["config"]))
        if current["config"].get(name) != comparison["config"].get(name)
    ]
    for name in ("calendar", "request", "software"):
        if current.get(name) != comparison.get(name):
            changes.append(name)
    current_ids = {
        member["customer_id"]
        for member in cell["members"]
        if member["day_type"] == kind
    }
    other_ids = (
        {
            member["customer_id"]
            for member in other["members"]
            if member["day_type"] == kind
        }
        if other
        else set()
    )
    label = (
        f"So với lần nghiên cứu {comparison['run_id'][:12]} · tham số đổi: {', '.join(f'{field_label(name)} ({name})' for name in changes) or 'không'} · "
        f"mẫu chỉ ở lần hiện tại: {len(current_ids - other_ids)}; chỉ ở lần so sánh: {len(other_ids - current_ids)}"
    )
    key = "sample" if selection.scope == "sample_portfolio" else "energy"
    if not other or kind not in other["result"][key]:
        return label + " · không có đường cong tương ứng"
    try:
        vector = convert_curve(
            other["result"][key][kind],
            comparison["config"]["interval_minutes"],
            selection.interval_minutes,
            selection.unit,
            selection.normalization,
        )
    except ValueError:
        return label + " · chọn độ phân giải thô hơn để so sánh"
    if vector is not None:
        figure.axes[0].plot(
            [index * selection.interval_minutes / 60 for index in range(len(vector))],
            vector,
            linestyle="--",
            color="#B04B2A",
            label="Lần so sánh",
            gid="comparison",
        )
        figure.axes[0].legend(fontsize=8)
        for row, value in zip(records, vector, strict=True):
            row["Lần so sánh"] = float(value)
            row["Chênh lệch"] = row["Chung"] - float(value)
    return label
