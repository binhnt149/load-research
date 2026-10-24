"""Explicit synthetic benchmarks with measured resources and disk preflight."""

import csv
import os
import platform
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil
import pyarrow as pa
import pyarrow.parquet as pq

from load_research.application.models import SourceInput, StudyRequest
from load_research.application.pipeline import run_study
from load_research.calendar import month_days
from load_research.domain.config import RunConfig, SourceOptions
from load_research.exports import export_study
from load_research.workspace import Workspace, atomic_json


def _disk_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            continue  # atomic writers can remove their temporary name between observations
    return total


def _dataset(root: Path, customers: int, periods: tuple[str, ...]) -> StudyRequest:
    mdms, cmis, billing = (
        root / name for name in ("mdms.parquet", "cmis.csv", "billing.csv")
    )
    schema = pa.schema(
        [
            ("meter_id", pa.string()),
            ("date", pa.string()),
            ("source_quality_flag", pa.string()),
        ]
        + [(f"slot_{slot:02}", pa.float64()) for slot in range(1, 49)]
    )
    totals: dict[tuple[str, str], float] = {}
    batch: list[dict] = []
    with (
        pq.ParquetWriter(mdms, schema, compression="zstd") as writer,
        cmis.open("w", newline="", encoding="utf-8") as stream,
    ):
        catalog = csv.writer(stream)
        catalog.writerow(["customer_id", "industry_code", "meter_id"])
        for index in range(customers):
            identifier, meter = f"{index + 1:06}", f"M{index + 1:06}"
            industry = "01" if index < customers // 2 else "02"
            catalog.writerow([identifier, industry, meter])
            level = 1 + index % 17 / 10
            for period in periods:
                for day in month_days(period):
                    values = [
                        level
                        * (1.6 if ((7 <= slot / 2 < 18) == (index % 2 == 0)) else 0.4)
                        * (1 if day.weekday() < 5 else 0.6)
                        for slot in range(48)
                    ]
                    batch.append(
                        {
                            "meter_id": meter,
                            "date": day.isoformat(),
                            "source_quality_flag": "actual",
                            **{
                                f"slot_{slot:02}": value
                                for slot, value in enumerate(values, 1)
                            },
                        }
                    )
                    totals[industry, period] = (
                        totals.get((industry, period), 0) + sum(values) * 100
                    )
                    if len(batch) >= 512:
                        writer.write_table(pa.Table.from_pylist(batch, schema=schema))
                        batch.clear()
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=schema))
    with billing.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["industry_code", "year_month", "billing_energy", "unit", "billing_basis"]
        )
        writer.writerows(
            [
                [industry, period, value, "kWh", "calendar_month"]
                for (industry, period), value in sorted(totals.items())
            ]
        )
    return StudyRequest(
        RunConfig(periods=periods, scope="SYNTHETIC-BENCHMARK", memory_limit_mb=512),
        (str(cmis),),
        (
            SourceInput(
                str(mdms), SourceOptions(values_already_scaled=True, layout="wide")
            ),
        ),
        (str(billing),),
    )


def run_benchmark(
    destination: Path,
    *,
    customers: int = 100,
    months: int = 1,
    year: int = 2025,
    full_size: bool = False,
) -> dict:
    if (
        type(customers) is not int
        or customers < 20
        or customers % 2
        or not 1 <= months <= 12
    ):
        raise ValueError(
            "benchmark requires an even customer count >=20 and 1..12 months"
        )
    datetime(year, 1, 1)
    periods = tuple(f"{year:04}-{month:02}" for month in range(1, months + 1))
    count = customers * sum(len(month_days(period)) * 48 for period in periods)
    if count > 5_000_000 and not full_size:
        raise ValueError("large benchmark requires explicit --full-size")
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("benchmark destination already exists")
    destination.mkdir(parents=True)
    report: dict = {
        "started_at": datetime.now().astimezone().isoformat(),
        "status": "preflight",
        "dimensions": {
            "customers": customers,
            "months": months,
            "year": year,
            "interval_values": count,
        },
        "full_scale": customers == 7000 and months == 12,
        "machine": {
            "os": platform.platform(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
            "physical_ram_bytes": psutil.virtual_memory().total,
        },
        "targets_proposed_only": {"seconds": 7200, "peak_rss_bytes": 10 * 1024**3},
        "preflight": {
            "free_disk_bytes": shutil.disk_usage(destination).free,
            "estimated_required_bytes": count * 240 + 256 * 1024**2,
        },
    }
    if (
        report["preflight"]["free_disk_bytes"]
        < report["preflight"]["estimated_required_bytes"]
    ):
        report.update(
            status="preflight_blocked",
            reason="insufficient_disk_for_canonical_and_temporary_data",
        )
        atomic_json(destination / "benchmark-report.json", report)
        return report
    measured: dict = {"peak_rss_bytes": 0, "sampled_peak_disk_bytes": 0}
    stop = threading.Event()
    process = psutil.Process()

    def monitor() -> None:
        while not stop.is_set():
            measured["peak_rss_bytes"] = max(
                measured["peak_rss_bytes"], process.memory_info().rss
            )
            measured["sampled_peak_disk_bytes"] = max(
                measured["sampled_peak_disk_bytes"], _disk_bytes(destination)
            )
            stop.wait(0.1)

    thread = threading.Thread(target=monitor, daemon=True)
    started = time.perf_counter()
    thread.start()
    try:
        sources = destination / "sources"
        sources.mkdir()
        request = _dataset(sources, customers, periods)
        atomic_json(destination / "request.json", request.to_dict())
        generated = time.perf_counter()
        result = run_study(Workspace.create(destination / "project"), request)
        export_study(result, destination / "report")
        report.update(
            status=result["status"],
            run_id=result["run_id"],
            software=result["software"],
            maximum_balance_error_kwh=max(
                cell["result"]["diagnostics"].get("balance_error_kwh", 0) or 0
                for cell in result["cells"]
            ),
        )
        measured.update(
            generation_seconds=generated - started,
            analysis_export_seconds=time.perf_counter() - generated,
        )
    except Exception as error:
        report.update(
            status="failed", error={"type": type(error).__name__, "message": str(error)}
        )
        raise
    finally:
        stop.set()
        thread.join()
        measured.update(
            total_seconds=time.perf_counter() - started,
            final_disk_bytes=_disk_bytes(destination),
        )
        report["measured"] = measured
        report["interpretation"] = (
            "Actual measurements for these dimensions only; a small run does not establish AC-24. Disk and RSS peaks sampled every 100ms."
        )
        atomic_json(destination / "benchmark-report.json", report)
    return report
