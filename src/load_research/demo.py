"""Deterministic, synthetic file exports for a complete local demonstration."""

import csv
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from load_research.application.models import SourceInput, StudyRequest
from load_research.calendar import ResearchCalendar, month_days
from load_research.domain.config import RunConfig, SourceOptions


def create_demo(
    destination: Path, *, customers: int = 60, period: str = "2024-02", seed: int = 42
) -> Path:
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError("demo destination already exists")
    if customers < 2 or customers % 2 or customers > 10000:
        raise ValueError("demo customers must be an even integer from 2 to 10000")
    dates = month_days(period)
    rng = np.random.default_rng(seed)
    records = []
    totals = {"01": 0.0, "02": 0.0}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".load-research-demo-", dir=destination.parent
    ) as temporary:
        staging = Path(temporary)
        with (staging / "mdms.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "meter_id",
                    "timestamp",
                    "value",
                    "source_quality_flag",
                    "unit",
                    "direction",
                    "interval_minutes",
                ]
            )
            for index in range(customers):
                identifier, meter = f"{index + 1:06}", f"M{index + 1:06}"
                industry = "01" if index < customers // 2 else "02"
                level = float(rng.uniform(1, 5))
                sample_total = 0.0
                for day in dates:
                    for slot in range(48):
                        hour = slot / 2
                        working = (
                            7 <= hour < 18 if index % 2 == 0 else hour < 7 or hour >= 18
                        )
                        energy = (
                            level
                            * (1.6 if working else 0.4)
                            * (1 if day.weekday() < 5 else 0.6)
                        )
                        timestamp = datetime.combine(
                            day, datetime.min.time()
                        ) + timedelta(minutes=slot * 30)
                        writer.writerow(
                            [
                                meter,
                                timestamp.isoformat(),
                                format(energy, ".15g"),
                                "actual",
                                "kWh",
                                "import",
                                30,
                            ]
                        )
                        sample_total += energy
                totals[industry] += sample_total * 100
                records.append(
                    [
                        identifier,
                        industry,
                        meter,
                        period,
                        sample_total,
                        "calendar_month",
                    ]
                )
        with (staging / "cmis.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "customer_id",
                    "industry_code",
                    "meter_id",
                    "year_month",
                    "sample_billing_kwh",
                    "sample_billing_basis",
                ]
            )
            writer.writerows(records)
        with (staging / "billing.csv").open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "industry_code",
                    "year_month",
                    "billing_energy",
                    "unit",
                    "billing_basis",
                    "organization_scope",
                    "source_description",
                ]
            )
            writer.writerows(
                [
                    [
                        industry,
                        period,
                        value,
                        "kWh",
                        "calendar_month",
                        "DEMO",
                        "Synthetic sample × 100; not customer data",
                    ]
                    for industry, value in totals.items()
                ]
            )
        calendar = ResearchCalendar()
        request = StudyRequest(
            RunConfig(
                periods=(period,), scope="DEMO", min_customers=min(10, customers // 2)
            ),
            ("cmis.csv",),
            (SourceInput("mdms.csv", SourceOptions(values_already_scaled=True)),),
            ("billing.csv",),
            calendar,
        )
        (staging / "request.json").write_text(
            json.dumps(request.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (staging / "README.txt").write_text(
            "SYNTHETIC DATA ONLY. Two industries, two behavioural shapes, one calendar month.\n",
            encoding="utf-8",
        )
        if destination.exists():
            raise FileExistsError("demo destination was created by another operation")
        os.rename(staging, destination)
    return destination / "request.json"
