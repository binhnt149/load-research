from pathlib import Path

from load_research.charts import build_figure, export_charts


def test_chart_uses_interval_average_power_and_exports_real_png_svg(tmp_path):
    cell = {
        "industry_code": "../escape",
        "year_month": "2024-02",
        "result": {
            "status": "valid",
            "energy": {"weekday": [10.0, 20.0] * 24},
            "sample": {"weekday": [10.0, 20.0] * 24},
            "contributions": {"weekday": {"group_1": [10.0, 20.0] * 24}},
            "sample_contributions": {"weekday": {"group_1": [10.0, 20.0] * 24}},
        },
    }
    figure = build_figure(cell, "weekday", 30, target_minutes=60, unit="kW")
    assert list(figure.axes[0].lines[0].get_ydata()) == [30.0] * 24
    assert "kW" in figure.axes[0].get_ylabel()
    result = {"run_id": "a" * 32, "config": {"interval_minutes": 30}, "cells": [cell]}
    paths = export_charts(result, tmp_path / "charts", formats=("png", "svg"))
    assert len(paths) == 2
    assert all(Path(path).parent == tmp_path / "charts" for path in paths)
    png = next(path for path in paths if path.suffix == ".png")
    assert png.read_bytes().startswith(b"\x89PNG")
    assert "<svg" in next(path for path in paths if path.suffix == ".svg").read_text()
