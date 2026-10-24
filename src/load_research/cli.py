"""Local automation using exactly the same pipeline as the desktop application."""

import argparse
import json
import sys
from pathlib import Path

from load_research.application.models import load_request
from load_research.application.pipeline import run_study
from load_research.benchmark import run_benchmark
from load_research.demo import create_demo
from load_research.exports import export_study
from load_research.workspace import Workspace


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="load-research",
        description="Local desktop load research; all source data stays on this computer.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser(
        "demo", help="create synthetic CMIS/MDMS/billing and a portable request"
    )
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument("--customers", type=int, default=60)
    demo.add_argument("--period", default="2024-02")
    run = commands.add_parser(
        "run", help="execute a JSON request and optionally export its results"
    )
    run.add_argument("--request", type=Path, required=True)
    run.add_argument("--project", type=Path, required=True)
    run.add_argument("--export", type=Path)
    run.add_argument("--unit", choices=("kW", "kWh"), default="kW")
    run.add_argument("--interval-minutes", type=int, choices=(30, 60))
    run.add_argument("--layout", choices=("wide", "long"), default="wide")
    run.add_argument("--csv-only", action="store_true")
    run.add_argument("--charts", nargs="*", choices=("png", "svg"), default=[])
    benchmark = commands.add_parser(
        "benchmark", help="measure a synthetic workload; large runs require --full-size"
    )
    benchmark.add_argument("--output", type=Path, required=True)
    benchmark.add_argument("--customers", type=int, default=100)
    benchmark.add_argument("--months", type=int, default=1)
    benchmark.add_argument("--year", type=int, default=2025)
    benchmark.add_argument("--full-size", action="store_true")
    args = parser.parse_args(arguments)
    try:
        if args.command == "demo":
            print(
                json.dumps(
                    {
                        "request": str(
                            create_demo(
                                args.output,
                                customers=args.customers,
                                period=args.period,
                            )
                        )
                    }
                )
            )
            return 0
        if args.command == "benchmark":
            report = run_benchmark(
                args.output,
                customers=args.customers,
                months=args.months,
                year=args.year,
                full_size=args.full_size,
            )
            print(json.dumps(report, ensure_ascii=False))
            return (
                0 if report["status"] in ("completed", "completed_with_warnings") else 2
            )
        request = load_request(args.request)
        workspace = (
            Workspace.open(args.project)
            if (args.project / "project.json").exists()
            else Workspace.create(args.project)
        )
        result = run_study(
            workspace,
            request,
            on_progress=lambda event: print(
                json.dumps(event, ensure_ascii=False), file=sys.stderr
            ),
        )
        if args.export:
            export_study(
                result,
                args.export,
                unit=args.unit,
                interval_minutes=args.interval_minutes,
                layout=args.layout,
                include_xlsx=not args.csv_only,
                chart_formats=tuple(args.charts),
            )
        print(
            json.dumps(
                {
                    "run_id": result["run_id"],
                    "status": result["status"],
                    "cells": len(result["cells"]),
                    "project": str(workspace.root),
                    "export": str(args.export) if args.export else None,
                }
            )
        )
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(
            json.dumps(
                {"error": type(error).__name__, "message": str(error)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
