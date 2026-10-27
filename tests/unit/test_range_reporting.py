import csv

from test_result_range import two_months

from load_research.result_range import build_range_view
from load_research.result_reporting import (
    export_views,
    interval_records,
    render_view,
    report_rows,
)
from load_research.result_view import ResultSelection


def test_range_tables_reports_and_chart_retain_all_dates_and_units(tmp_path):
    result, daily = two_months()
    view = build_range_view(
        result,
        ResultSelection("2024-04", unit="kWh"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    rows = interval_records(view)
    assert len(rows) == 96
    assert rows[48]["Ngày"] == "2024-05-01" and rows[48]["Chu kỳ"] == 1
    long = [
        r for r in report_rows(view, "long") if r["Loại đường biểu diễn"] == "Tổng hợp"
    ]
    assert (
        len(long) == 96
        and long[48]["Tháng"] == "2024-05"
        and long[48]["Ngày"] == "2024-05-01"
    )
    wide = [
        r for r in report_rows(view, "wide") if r["Loại đường biểu diễn"] == "Tổng hợp"
    ]
    assert len(wide) == 2 and wide[1]["Chu kỳ 01"] == 36
    assert render_view(view).axes[0].get_xlabel() == "Ngày / giờ"
    output = export_views(
        result, [view], tmp_path / "range", layout="wide", chart_formats=("png",)
    )
    with (output / "profiles.csv").open(encoding="utf-8-sig") as stream:
        report = list(csv.DictReader(stream))
    assert {r["Ngày"] for r in report} == {"2024-04-30", "2024-05-01"}


def test_range_member_export_respects_month_daytype_pairs(tmp_path):
    import copy

    result, daily = two_months()
    result["calendar"] = {
        "overrides": {"2024-04-30": "saturday", "2024-05-01": "sunday"}
    }
    expected = set()
    for cell in result["cells"]:
        for key in ("energy", "sample", "contributions", "sample_contributions"):
            cell["result"][key]["sunday"] = copy.deepcopy(
                cell["result"][key]["weekday"]
            )
        cell["day_counts"]["sunday"] = 1
        cell["members"] = [
            {
                "customer_id": f"{cell['industry_code']}-{cell['year_month']}-{kind}",
                "day_type": kind,
                "cluster_id": "group_1",
                "weight": 1,
            }
            for kind in ("saturday", "sunday")
        ]
        kind = "saturday" if cell["year_month"] == "2024-04" else "sunday"
        expected.add(f"{cell['industry_code']}-{cell['year_month']}-{kind}")
        daily[cell["year_month"]][cell["industry_code"]]["day_types"] = [kind]
    view = build_range_view(
        result,
        ResultSelection("2024-04"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    output = export_views(
        result, [view], tmp_path / "members", include_xlsx=False, include_members=True
    )
    with (output / "cluster-members.csv").open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["Mã khách hàng"] for row in rows} == expected


def test_hidden_chart_series_does_not_remove_numerical_report_rows():
    result, daily = two_months()
    view = build_range_view(
        result,
        ResultSelection("2024-04"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    overall = view["series"][0]
    view["hidden_series_ids"] = [overall["id"]]
    axes = render_view(view).axes[0]
    assert overall["id"] not in {line.get_gid() for line in axes.lines}
    assert any(row["Loại đường biểu diễn"] == "Tổng hợp" for row in report_rows(view))


def test_time_axis_uses_numeric_dates_instead_of_english_month_names():
    import re

    from matplotlib.backends.backend_agg import FigureCanvasAgg

    result, daily = two_months()
    view = build_range_view(
        result,
        ResultSelection("2024-04"),
        daily,
        "2024-04-30",
        "2024-05-01",
        method="representative",
    )
    figure = render_view(view)
    FigureCanvasAgg(figure).draw()
    labels = [t.get_text() for t in figure.axes[0].get_xticklabels()] + [
        figure.axes[0].xaxis.get_offset_text().get_text()
    ]
    assert not any(re.search("[A-Za-z]", text) for text in labels)
