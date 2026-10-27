"""Bounded-batch disk storage and complete customer-month grids."""

import itertools
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa

from load_research.calendar import month_days
from load_research.importers.catalog import Catalog, Customer
from load_research.importers.metering import MeterRecord


@dataclass
class MonthGrid:
    customer: Customer
    period: str
    values: np.ndarray
    estimated: np.ndarray
    quality_known: np.ndarray
    repair_blocked: np.ndarray | None = None


class IntervalStore:
    def __init__(
        self,
        path: Path,
        *,
        memory_limit_mb: int = 4096,
        threads: int = 2,
        read_only: bool = False,
    ) -> None:
        if (
            type(memory_limit_mb) is not int
            or memory_limit_mb < 64
            or type(threads) is not int
            or threads < 1
        ):
            raise ValueError("invalid database resource limits")
        self._read_only = read_only
        self.connection = duckdb.connect(
            str(path),
            read_only=read_only,
            config={
                "memory_limit": f"{memory_limit_mb}MB",
                "threads": str(threads),
                "enable_external_access": "false",
                "autoload_known_extensions": "false",
                "autoinstall_known_extensions": "false",
            },
        )
        if not read_only:
            self.connection.execute("""
            CREATE TABLE IF NOT EXISTS raw_intervals (
                customer_id VARCHAR, industry_code VARCHAR, meter_id VARCHAR,
                start TIMESTAMP, minutes SMALLINT, energy_kwh DOUBLE,
                estimated BOOLEAN, quality_known BOOLEAN, source_id VARCHAR, source_row BIGINT,
                repair_blocked BOOLEAN
            )
        """)
        self._validated = False

    def __enter__(self) -> "IntervalStore":
        return self

    def __exit__(self, *_args) -> None:
        self.connection.close()

    @property
    def raw_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM raw_intervals").fetchone()
        if row is None:
            raise RuntimeError("database did not return an interval count")
        return int(row[0])

    def append(self, records: Iterable[MeterRecord], batch_size: int = 20000) -> None:
        if not 1 <= batch_size <= 1_000_000:
            raise ValueError("invalid batch size")
        names = [field.name for field in fields(MeterRecord)]
        source = iter(records)
        self._validated = False
        while batch := list(itertools.islice(source, batch_size)):
            table = pa.table(
                {name: [getattr(record, name) for record in batch] for name in names}
            )
            self.connection.register("incoming_batch", table)
            try:
                self.connection.execute(
                    "INSERT INTO raw_intervals SELECT * FROM incoming_batch"
                )
            finally:
                self.connection.unregister("incoming_batch")

    def validate(self) -> None:
        conflict = self.connection.execute("""
            SELECT meter_id FROM raw_intervals GROUP BY meter_id, start, minutes
            HAVING COUNT(DISTINCT (customer_id, industry_code, energy_kwh, estimated, quality_known, repair_blocked)) > 1
            LIMIT 1
        """).fetchone()
        if conflict:
            raise ValueError(
                "conflicting duplicate intervals require explicit source resolution"
            )
        if not self._read_only:
            self.connection.execute("""
            CREATE OR REPLACE VIEW clean_intervals AS
            SELECT customer_id, industry_code, meter_id, start, minutes, energy_kwh,
                estimated, quality_known,
                FIRST(source_id ORDER BY source_id, source_row) AS source_id,
                FIRST(source_row ORDER BY source_id, source_row) AS source_row, repair_blocked
            FROM raw_intervals
            GROUP BY customer_id, industry_code, meter_id, start, minutes, energy_kwh, estimated, quality_known, repair_blocked
        """)
        overlap = self.connection.execute("""
            SELECT meter_id FROM (
                SELECT meter_id, start,
                    LAG(start + minutes * INTERVAL '1 minute') OVER (PARTITION BY meter_id ORDER BY start) AS previous_end
                FROM clean_intervals
            ) WHERE previous_end > start LIMIT 1
        """).fetchone()
        if overlap:
            raise ValueError("overlapping meter intervals require explicit resolution")
        self._validated = True

    def iter_records(self, period: str) -> Iterator[MeterRecord]:
        if not self._validated:
            raise ValueError("interval store must be validated before reading")
        days = month_days(period)
        start = datetime.combine(days[0], datetime.min.time())
        end = datetime.combine(days[-1] + timedelta(days=1), datetime.min.time())
        cursor = self.connection.execute(
            """
            SELECT * FROM clean_intervals WHERE start >= ? AND start < ?
            ORDER BY customer_id, meter_id, start
        """,
            (start, end),
        )
        while batch := cursor.fetchmany(20000):
            for row in batch:
                yield MeterRecord(*row)

    def iter_customer_months(
        self, period: str, target_minutes: int, catalog: Catalog
    ) -> Iterator[MonthGrid]:
        if target_minutes not in (30, 60):
            raise ValueError("analysis resolution must be 30 or 60 minutes")
        eligible, _excluded = catalog.month_customers(period)
        seen = set()
        for customer_id, records in itertools.groupby(
            self.iter_records(period), key=lambda row: row.customer_id
        ):
            if customer_id in eligible:
                seen.add(customer_id)
                yield self._month_grid(
                    eligible[customer_id], records, period, target_minutes, catalog
                )
        for customer_id in sorted(set(eligible) - seen):
            yield self._month_grid(
                eligible[customer_id], (), period, target_minutes, catalog
            )

    def customer_month(
        self, period: str, customer_id: str, target_minutes: int, catalog: Catalog
    ) -> MonthGrid:
        if not self._validated:
            raise ValueError("interval store must be validated before reading")
        customers, _excluded = catalog.month_customers(period)
        if customer_id not in customers:
            raise ValueError(
                "customer is not active with stable identity for the complete month"
            )
        return self._read_customer_month(
            period, customers[customer_id], target_minutes, catalog
        )

    def inspection_month(
        self, period: str, customer_id: str, target_minutes: int, catalog: Catalog
    ) -> MonthGrid:
        links = catalog.by_customer.get(customer_id)
        if not links:
            raise ValueError("Mã khách hàng không có trong danh mục mẫu.")
        return self._read_customer_month(
            period, links[0].customer, target_minutes, catalog
        )

    def _read_customer_month(
        self, period: str, customer: Customer, target_minutes: int, catalog: Catalog
    ) -> MonthGrid:
        if not self._validated:
            raise ValueError("interval store must be validated before reading")
        days = month_days(period)
        cursor = self.connection.execute(
            "SELECT * FROM clean_intervals WHERE customer_id = ? AND start >= ? AND start < ? ORDER BY meter_id, start",
            (
                customer.customer_id,
                datetime.combine(days[0], datetime.min.time()),
                datetime.combine(days[-1] + timedelta(days=1), datetime.min.time()),
            ),
        )

        def records() -> Iterator[MeterRecord]:
            while batch := cursor.fetchmany(20000):
                yield from (MeterRecord(*row) for row in batch)

        return self._month_grid(customer, records(), period, target_minutes, catalog)

    @staticmethod
    def _month_grid(
        customer: Customer,
        records: Iterable[MeterRecord],
        period: str,
        minutes: int,
        catalog: Catalog,
    ) -> MonthGrid:
        days = month_days(period)
        shape = (len(days), 1440 // minutes)
        start = datetime.combine(days[0], datetime.min.time())
        buffers: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
        repair_blocked = np.zeros(shape, bool)
        for record in records:
            if record.minutes > minutes:
                raise ValueError(
                    "source resolution cannot produce requested analysis resolution"
                )
            if record.meter_id not in buffers:
                buffers[record.meter_id] = (
                    np.zeros(shape),
                    np.zeros(shape),
                    np.zeros(shape, bool),
                    np.ones(shape, bool),
                )
            energy, covered, estimated, known = buffers[record.meter_id]
            day = (record.start.date() - days[0]).days
            slot = (record.start.hour * 60 + record.start.minute) // minutes
            if record.energy_kwh is not None:
                energy[day, slot] += record.energy_kwh
                covered[day, slot] += record.minutes
            estimated[day, slot] |= record.estimated
            known[day, slot] &= record.quality_known
            repair_blocked[day, slot] |= record.repair_blocked
        total, complete = np.zeros(shape), np.ones(shape, bool)
        total_estimated, total_known = np.zeros(shape, bool), np.ones(shape, bool)
        any_active = np.zeros(shape, bool)
        starts = np.datetime64(start, "m") + (
            np.arange(np.prod(shape)) * minutes
        ).reshape(shape).astype("timedelta64[m]")
        ends = starts + np.timedelta64(minutes, "m")
        meters = {link.meter_id for link in catalog.by_customer[customer.customer_id]}
        for meter in meters:
            expected = np.zeros(shape)
            for link in catalog.by_customer[customer.customer_id]:
                if link.meter_id == meter:
                    overlap = np.minimum(
                        ends, np.datetime64(link.valid_to, "m")
                    ) - np.maximum(starts, np.datetime64(link.valid_from, "m"))
                    expected += np.maximum(0, overlap / np.timedelta64(1, "m"))
            energy, covered, estimated, known = buffers.get(
                meter,
                (
                    np.zeros(shape),
                    np.zeros(shape),
                    np.zeros(shape, bool),
                    np.ones(shape, bool),
                ),
            )
            active = expected > 0
            any_active |= active
            complete &= ~active | (covered == expected)
            total += energy
            total_estimated |= estimated & active
            total_known &= ~active | known
        complete &= any_active
        repair_blocked[~any_active] = True
        total[~complete] = np.nan
        total_known[~complete] = False
        return MonthGrid(
            customer, period, total, total_estimated, total_known, repair_blocked
        )
