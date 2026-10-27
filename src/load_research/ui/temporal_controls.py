"""Range/customer controls and strict ownership of asynchronous chart responses."""

from dataclasses import asdict
from uuid import uuid4

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QLabel, QWidget

from load_research.calendar import month_days
from load_research.customer_view import convert_temporal_view
from load_research.result_range import range_dates


class TemporalControls(QWidget):
    changed = Signal()
    requested = Signal(dict)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.token = None
        self.cached_view = None
        self.cached_context = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.start, self.end = QDateEdit(), QDateEdit()
        for label, control in [("Từ", self.start), ("Đến", self.end)]:
            control.setCalendarPopup(True)
            control.setDisplayFormat("yyyy-MM-dd")
            control.setAccessibleName(
                "Từ ngày" if control is self.start else "Đến ngày"
            )
            control.setMinimumWidth(112)
            layout.addWidget(QLabel(label))
            layout.addWidget(control, 1)
            control.dateChanged.connect(self.changed)
        self.customer_label = QLabel("Khách hàng")
        self.customer = QComboBox()
        self.customer.setEditable(True)
        self.customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.customer.setMinimumContentsLength(8)
        self.customer.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.customer.setAccessibleName("Tìm mã khách hàng mẫu")
        completer = self.customer.completer()
        assert completer is not None
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.customer.currentTextChanged.connect(self.changed)
        layout.addWidget(self.customer_label)
        layout.addWidget(self.customer, 1)
        self.set_mode("representative")

    def reset(self, result):
        self.cached_view, self.cached_context, self.token = None, None, None
        periods = result["config"].get("periods") or sorted(
            {c["year_month"] for c in result["cells"]}
        )
        self.blockSignals(True)
        if periods:
            first, last = month_days(min(periods))[0], month_days(max(periods))[-1]
            low, high = (
                QDate(first.year, first.month, first.day),
                QDate(last.year, last.month, last.day),
            )
            for control in (self.start, self.end):
                control.setDateRange(low, high)
                control.setDate(low)
        identifiers = {
            m["customer_id"] for c in result["cells"] for m in c.get("members", [])
        }
        identifiers.update(
            i for q in result.get("quality", []) for i in q.get("excluded", {})
        )
        self.customer.clear()
        self.customer.addItems(sorted(identifiers))
        self.blockSignals(False)

    def set_mode(self, mode):
        self.setVisible(mode in ("range", "customer"))
        self.customer_label.setVisible(mode == "customer")
        self.customer.setVisible(mode == "customer")

    def context(self):
        owner = self.owner
        selection = asdict(owner.selection())
        selection.update(
            interval_minutes=owner.result["config"]["interval_minutes"],
            unit="kWh",
            normalization=None,
        )
        return {
            "run_id": owner.result["run_id"],
            "date_start": self.start.date().toString("yyyy-MM-dd"),
            "mode": owner.mode.currentData(),
            "date_end": self.end.date().toString("yyyy-MM-dd"),
            "selection": selection,
            "method": owner.daily_method.currentData(),
            "customer_id": self.customer.currentText().strip()
            if owner.mode.currentData() == "customer"
            else "",
            "component_catalog_revision": None
            if owner.component_catalog is None
            else owner.component_catalog["revision"],
        }

    def request(self):
        context = self.context()
        customer = self.owner.mode.currentData() == "customer"
        if customer and not context["customer_id"]:
            raise ValueError("Hãy chọn hoặc nhập mã khách hàng mẫu.")
        range_dates(
            self.owner.result,
            context["date_start"],
            context["date_end"],
            () if customer else context["selection"]["day_types"],
        )
        self.token = uuid4().hex
        self.requested.emit({**context, "token": self.token})

    def accept_data(self, view, context, token):
        if (
            token != self.token
            or self.owner.mode.currentData() not in ("range", "customer")
            or context != self.context()
        ):
            return False
        self.cached_view, self.cached_context = view, context
        return True

    def current(self):
        if self.cached_context != self.context() or self.cached_view is None:
            return None
        return convert_temporal_view(self.cached_view, self.owner.selection())
