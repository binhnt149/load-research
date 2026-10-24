"""Explicit sample, meter relationship and industry billing contracts."""

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from load_research.calendar import month_days
from load_research.domain.energy import ENERGY_UNITS


def required_text(row: dict, name: str) -> str:
    value = str(row.get(name, "")).strip()
    if not value or len(value) > 256:
        raise ValueError(f"missing or invalid {name}")
    return value


def number(value: object, *, nonnegative: bool = True, decimal: str = ".") -> float:
    parsed = float(str(value).replace(decimal, "."))
    if not math.isfinite(parsed) or (nonnegative and parsed < 0):
        raise ValueError("number must be finite and non-negative")
    return parsed


@dataclass(frozen=True)
class Customer:
    customer_id: str
    industry_code: str
    weight: float = 1.0


@dataclass(frozen=True)
class MeterLink:
    customer: Customer
    meter_id: str
    valid_from: datetime
    valid_to: datetime
    additive: bool = False


@dataclass(frozen=True)
class BillingTotal:
    energy_kwh: float
    basis: str
    source_description: str


@dataclass(frozen=True)
class SampleBilling:
    energy_kwh: float
    basis: str | None


class Catalog:
    def __init__(
        self,
        links: list[MeterLink],
        scope: str,
        sample_billing: dict,
        industry_names: dict[str, str] | None = None,
    ) -> None:
        self.links = links
        self.scope = scope
        self.sample_billing = sample_billing
        self.industry_names = industry_names or {}
        self.by_meter: dict[str, list[MeterLink]] = defaultdict(list)
        self.by_customer: dict[str, list[MeterLink]] = defaultdict(list)
        for link in links:
            self.by_meter[link.meter_id].append(link)
            self.by_customer[link.customer.customer_id].append(link)
        for meter_links in self.by_meter.values():
            ordered = sorted(meter_links, key=lambda link: link.valid_from)
            if any(
                left.valid_to > right.valid_from
                for left, right in zip(ordered, ordered[1:], strict=False)
            ):
                raise ValueError("ambiguous meter mapping")
        for customer_links in self.by_customer.values():
            for index, left in enumerate(customer_links):
                for right in customer_links[index + 1 :]:
                    if max(left.valid_from, right.valid_from) < min(
                        left.valid_to, right.valid_to
                    ):
                        if left.customer != right.customer or not (
                            left.additive and right.additive
                        ):
                            raise ValueError(
                                "overlapping customer meter mapping requires declared additive meters"
                            )

    def resolve(self, meter_id: str, timestamp: datetime) -> Customer:
        local = timestamp.replace(tzinfo=None)
        matches = [
            link.customer
            for link in self.by_meter.get(meter_id, ())
            if link.valid_from <= local < link.valid_to
        ]
        if len(matches) != 1:
            raise ValueError("missing or ambiguous meter mapping")
        return matches[0]

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "industry_names": self.industry_names,
            "links": [
                {
                    "customer_id": link.customer.customer_id,
                    "industry_code": link.customer.industry_code,
                    "sampling_weight": link.customer.weight,
                    "meter_id": link.meter_id,
                    "valid_from": link.valid_from.isoformat(),
                    "valid_to": link.valid_to.isoformat(),
                    "meter_role": "additive" if link.additive else "replacement",
                }
                for link in self.links
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Catalog":
        catalog = load_catalog(payload["links"], payload["scope"])
        catalog.industry_names = payload.get("industry_names", {})
        return catalog

    def active_meters(self, customer_id: str, timestamp: datetime) -> set[str]:
        return {
            link.meter_id
            for link in self.by_customer[customer_id]
            if link.valid_from <= timestamp < link.valid_to
        }

    def month_customers(
        self, period: str
    ) -> tuple[dict[str, Customer], dict[str, str]]:
        days = month_days(period)
        start = datetime.combine(days[0], datetime.min.time())
        end = datetime.combine(days[-1] + timedelta(days=1), datetime.min.time())
        eligible, excluded = {}, {}
        for identifier, links in self.by_customer.items():
            active = [
                link
                for link in links
                if link.valid_from < end and link.valid_to > start
            ]
            if not active:
                continue
            identities = {link.customer for link in active}
            cursor = start
            for link in sorted(active, key=lambda item: item.valid_from):
                if link.valid_from > cursor:
                    break
                cursor = max(cursor, link.valid_to)
            if len(identities) == 1 and cursor >= end:
                eligible[identifier] = active[0].customer
            else:
                excluded[identifier] = "partial_month_or_changed_industry_weight"
        return eligible, excluded


def load_catalog(rows: Iterable[dict], scope: str, *, decimal: str = ".") -> Catalog:
    links, seen = [], set()
    sample_billing: dict[tuple[str, str], SampleBilling] = {}
    industry_names: dict[str, str] = {}
    for row in rows:
        if row.get("organization_code", scope) != scope:
            raise ValueError("customer scope does not match study scope")
        identifier = required_text(row, "customer_id")
        customer = Customer(
            identifier,
            required_text(row, "industry_code"),
            number(row.get("sampling_weight") or 1, decimal=decimal),
        )
        if customer.weight <= 0:
            raise ValueError("sampling weight must be positive")
        if row.get("industry_name"):
            name = required_text(row, "industry_name")
            if industry_names.get(customer.industry_code, name) != name:
                raise ValueError("conflicting industry names")
            industry_names[customer.industry_code] = name
        meter_id = str(
            row.get("meter_id") or row.get("measurement_point_id") or ""
        ).strip()
        if not meter_id:
            raise ValueError("meter mapping requires meter_id or measurement_point_id")
        start = (
            datetime.fromisoformat(row["valid_from"])
            if row.get("valid_from")
            else datetime.min
        )
        end = (
            datetime.fromisoformat(row["valid_to"])
            if row.get("valid_to")
            else datetime.max
        )
        if start.tzinfo or end.tzinfo or start >= end:
            raise ValueError(
                "mapping validity must be an ordered local [from,to) interval"
            )
        link = MeterLink(
            customer,
            meter_id,
            start,
            end,
            str(row.get("meter_role", "")).lower() == "additive",
        )
        if link not in seen:
            seen.add(link)
            links.append(link)
        if row.get("sample_billing_kwh"):
            period = required_text(row, "year_month")
            month_days(period)
            basis = row.get("sample_billing_basis") or None
            if basis not in (None, "calendar_month", "billing_label_month"):
                raise ValueError("invalid sample billing basis")
            value = SampleBilling(
                number(row["sample_billing_kwh"], decimal=decimal), basis
            )
            key = (identifier, period)
            if key in sample_billing and sample_billing[key] != value:
                raise ValueError("conflicting sample billing")
            sample_billing[key] = value
    if not links:
        raise ValueError("sample catalog is empty")
    return Catalog(links, scope, sample_billing, industry_names)


def load_billing(
    rows: Iterable[dict], scope: str, *, decimal: str = "."
) -> dict[tuple[str, str], BillingTotal]:
    totals = {}
    for row in rows:
        if row.get("organization_scope", scope) != scope:
            raise ValueError("billing scope does not match study scope")
        industry, period = (
            required_text(row, "industry_code"),
            required_text(row, "year_month"),
        )
        month_days(period)
        basis = row.get("billing_basis", "")
        if basis not in ("calendar_month", "billing_label_month"):
            raise ValueError("billing basis must be explicitly declared")
        unit = row.get("unit", "")
        if unit not in ENERGY_UNITS:
            raise ValueError("billing energy unit must be declared")
        value = number(row.get("billing_energy"), decimal=decimal) * ENERGY_UNITS[unit]
        if not math.isfinite(value):
            raise ValueError("billing energy overflow")
        key = (industry, period)
        if key in totals:
            raise ValueError("duplicate industry-month billing total")
        totals[key] = BillingTotal(
            value,
            basis,
            str(row.get("source_description", "user-supplied billing table")),
        )
    return totals
