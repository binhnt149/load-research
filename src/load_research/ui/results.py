"""Computed curve filters, quality, cohort comparison and cluster display labels."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from load_research.charts import build_figure
from load_research.exports import apply_annotations, cluster_display_name, convert_curve
from load_research.ui.forms import choose, combo
from load_research.ui.models import RecordsModel


class ResultsView(QWidget):
    rename_requested = Signal(dict)
    export_requested = Signal(bool)
    inspect_requested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.result: dict | None = None
        self.comparison: dict | None = None
        self.annotations: list[dict] = []
        layout = QVBoxLayout(self)
        self.summary = QLabel("Chưa có kết quả")
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        filters = QHBoxLayout()
        self.industry, self.period, self.day_type, self.group = [
            QComboBox() for _ in range(4)
        ]
        for label, filter_widget in (
            ("Ngành", self.industry),
            ("Tháng", self.period),
            ("Loại ngày", self.day_type),
            ("Nhóm", self.group),
        ):
            filters.addWidget(QLabel(label))
            filters.addWidget(filter_widget, 1)
        layout.addLayout(filters)
        options = QHBoxLayout()
        self.resolution = combo([("48 chu kỳ", 30), ("24 chu kỳ", 60)])
        self.unit = combo([("Công suất kW", "kW"), ("Điện năng kWh", "kWh")])
        self.scope = combo(
            [
                ("Suy rộng toàn ngành", "industry_scaled"),
                ("Tổng hợp tập mẫu", "sample_portfolio"),
            ]
        )
        self.normalization = combo(
            [
                ("Giá trị vật lý", None),
                ("Chuẩn hoá: trung bình = 1", "mean"),
                ("Chuẩn hoá: tổng = 1", "share"),
                ("Chuẩn hoá: đỉnh = 1", "peak"),
            ]
        )
        self.components = QCheckBox("Hiện thành phần")
        self.components.setChecked(True)
        self.stacked = QCheckBox("Xếp chồng đóng góp")
        for widget in (
            self.scope,
            self.unit,
            self.resolution,
            self.normalization,
            self.components,
            self.stacked,
        ):
            options.addWidget(widget)
        layout.addLayout(options)
        self.comparison_label = QLabel()
        self.comparison_label.setWordWrap(True)
        self.comparison_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.comparison_label)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.canvas = FigureCanvasQTAgg(Figure(figsize=(10, 4)))
        self.canvas.setMinimumHeight(180)
        splitter.addWidget(self.canvas)
        tabs = QTabWidget()
        (
            self.table_model,
            self.quality_model,
            self.members_model,
            self.excluded_model,
        ) = [RecordsModel(self) for _ in range(4)]
        self.statistics_model, self.reconciliation_model = (
            RecordsModel(self),
            RecordsModel(self),
        )
        for label, model in (
            ("Chu kỳ", self.table_model),
            ("Chất lượng toàn tháng", self.quality_model),
            ("Khách hàng / nhóm", self.members_model),
            ("Khách hàng bị loại toàn tháng", self.excluded_model),
            ("Thống kê nhóm", self.statistics_model),
            ("Đối soát CMIS toàn tháng", self.reconciliation_model),
        ):
            view = QTableView()
            view.setModel(model)
            view.setSortingEnabled(True)
            view.setAlternatingRowColors(True)
            view.viewport().setAutoFillBackground(True)
            view.horizontalHeader().setResizeContentsPrecision(50)
            view.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            tabs.addTab(view, label)
        splitter.addWidget(tabs)
        splitter.setSizes([450, 220])
        layout.addWidget(splitter, 1)
        buttons = QHBoxLayout()
        inspect = QPushButton("Xem dữ liệu ngày / bù…")
        inspect.clicked.connect(self.inspect_dialog)
        rename = QPushButton("Đặt tên nhóm đang chọn…")
        rename.clicked.connect(self.rename_dialog)
        export_current, export_all = (
            QPushButton("Xuất lựa chọn…"),
            QPushButton("Xuất toàn bộ lần chạy…"),
        )
        export_current.clicked.connect(lambda: self.export_requested.emit(True))
        export_all.clicked.connect(lambda: self.export_requested.emit(False))
        for button in (inspect, rename, export_current, export_all):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.industry.currentIndexChanged.connect(self.refresh_periods)
        self.period.currentIndexChanged.connect(self.refresh_days)
        self.day_type.currentIndexChanged.connect(self.refresh_groups)
        for widget in (
            self.group,
            self.resolution,
            self.unit,
            self.scope,
            self.normalization,
        ):
            widget.currentIndexChanged.connect(self.render_results)
        self.components.toggled.connect(self.render_results)
        self.stacked.toggled.connect(self.render_results)

    @staticmethod
    def fill(widget: QComboBox, items: list[tuple[str, object]]) -> None:
        old = widget.currentData()
        widget.blockSignals(True)
        widget.clear()
        for label, value in items:
            widget.addItem(label, value)
        choose(widget, old)
        widget.blockSignals(False)

    def set_result(self, result: dict, annotations: list[dict] | None = None) -> None:
        self.result, self.annotations, self.comparison = result, annotations or [], None
        source_minutes = result["config"]["interval_minutes"]
        self.fill(
            self.resolution,
            [("48 chu kỳ", 30), ("24 chu kỳ", 60)]
            if source_minutes == 30
            else [("24 chu kỳ", 60)],
        )
        self.fill(
            self.industry,
            [
                (code, code)
                for code in sorted({cell["industry_code"] for cell in result["cells"]})
            ],
        )
        self.refresh_periods()

    def named_result(self) -> dict:
        if self.result is None:
            raise ValueError("no result is loaded")
        return apply_annotations(self.result, self.annotations)

    def export_options(self, *, selected: bool) -> dict:
        return {
            "interval_minutes": self.resolution.currentData(),
            "unit": self.unit.currentData(),
            "scope": self.scope.currentData(),
            "normalization": self.normalization.currentData(),
            "industry_codes": (self.industry.currentData(),) if selected else (),
            "periods": (self.period.currentData(),) if selected else (),
            "day_types": (self.day_type.currentData(),) if selected else (),
            "cluster_ids": (self.group.currentData(),)
            if selected and self.group.currentData()
            else (),
        }

    def current_cell(self) -> dict | None:
        if self.result is None:
            return None
        return next(
            (
                cell
                for cell in self.named_result()["cells"]
                if cell["industry_code"] == self.industry.currentData()
                and cell["year_month"] == self.period.currentData()
            ),
            None,
        )

    def refresh_periods(self) -> None:
        if self.result is not None:
            periods = sorted(
                {
                    cell["year_month"]
                    for cell in self.result["cells"]
                    if cell["industry_code"] == self.industry.currentData()
                }
            )
            self.fill(self.period, [(period, period) for period in periods])
            self.refresh_days()

    def refresh_days(self) -> None:
        cell = self.current_cell()
        if cell:
            labels = {
                "weekday": "Ngày thường",
                "saturday": "Thứ Bảy",
                "sunday": "Chủ nhật",
                "holiday": "Lễ",
            }
            self.fill(
                self.day_type,
                [
                    (labels[kind], kind)
                    for kind in ("weekday", "saturday", "sunday", "holiday")
                    if cell["day_counts"].get(kind, 0)
                ],
            )
        self.refresh_groups()

    def refresh_groups(self) -> None:
        cell, kind = self.current_cell(), self.day_type.currentData()
        if cell:
            names = cell.get("cluster_names", {}).get(kind, {})
            labels = sorted(
                set(cell["clusters"].get(kind, {}).get("assignments", {}).values())
            )
            self.fill(
                self.group,
                [("Tất cả nhóm", None)]
                + [
                    (
                        f"{names.get(label, cluster_display_name(label))} [{label}]",
                        label,
                    )
                    for label in labels
                ],
            )
        self.render_results()

    def set_resolution(self, minutes: int) -> None:
        if self.resolution.findData(minutes) < 0:
            raise ValueError("requested resolution is unavailable")
        choose(self.resolution, minutes)

    def set_normalization(self, kind: str | None) -> None:
        choose(self.normalization, kind)

    def set_comparison(self, result: dict | None) -> None:
        if (
            result
            and self.result
            and result["config"]["scope"] != self.result["config"]["scope"]
        ):
            raise ValueError("comparison requires the same organization scope")
        self.comparison = result
        self.render_results()

    def render_results(self) -> None:
        cell, kind = self.current_cell(), self.day_type.currentData()
        if self.result is None or cell is None or kind is None:
            return
        source, target = (
            self.result["config"]["interval_minutes"],
            self.resolution.currentData(),
        )
        unit, scope, normalization = (
            self.unit.currentData(),
            self.scope.currentData(),
            self.normalization.currentData(),
        )
        figure = build_figure(
            cell,
            kind,
            source,
            target_minutes=target,
            unit=unit,
            scope=scope,
            normalization=normalization,
            components=self.components.isChecked(),
            stacked=self.stacked.isChecked(),
            cluster_ids=(self.group.currentData(),) if self.group.currentData() else (),
            run_id=self.result["run_id"],
            figure=self.canvas.figure,
        )
        if normalization is None:
            figure.axes[0].set_ylabel(
                "Công suất\ntrung bình (kW)"
                if unit == "kW"
                else "Điện năng\nmỗi chu kỳ (kWh)"
            )
        computed = cell["result"]
        key = "sample" if normalization or scope == "sample_portfolio" else "energy"
        vector = (
            None
            if kind not in computed[key]
            else convert_curve(computed[key][kind], source, target, unit, normalization)
        )
        records = []
        if vector is not None:
            for index, value in enumerate(vector):
                start, end = index * target, (index + 1) * target
                records.append(
                    {
                        "Chu kỳ": index + 1,
                        "Bắt đầu": f"{start // 60:02}:{start % 60:02}",
                        "Kết thúc": f"{end // 60:02}:{end % 60:02}",
                        "Chung": float(value),
                    }
                )
            component_key = (
                "sample_contributions" if key == "sample" else "contributions"
            )
            for label, values in computed[component_key].get(kind, {}).items():
                if self.group.currentData() and self.group.currentData() != label:
                    continue
                curve = convert_curve(values, source, target, unit, normalization)
                if curve is not None:
                    display = (
                        cell.get("cluster_names", {})
                        .get(kind, {})
                        .get(label, cluster_display_name(label))
                    )
                    for row, value in zip(records, curve, strict=True):
                        row[f"{display} [{label}]"] = float(value)
        self.comparison_label.setText("")
        if self.comparison:
            self._compare(cell, kind, target, unit, normalization, key, figure, records)
        self.table_model.set_records(records)
        quality = [
            {
                key: value
                for key, value in row.items()
                if isinstance(value, (str, int, float))
            }
            for row in self.result.get("quality", [])
            if row["period"] == cell["year_month"]
        ]
        self.quality_model.set_records(quality)
        self.members_model.set_records(
            [member for member in cell["members"] if member["day_type"] == kind]
        )
        excluded = [
            {"customer_id": identifier, "reason": reason}
            for row in self.result.get("quality", [])
            if row["period"] == cell["year_month"]
            for identifier, reason in row.get("excluded", {}).items()
        ]
        self.excluded_model.set_records(excluded)
        diagnostics = computed["diagnostics"]
        billing_text = (
            "N/A"
            if computed.get("billing_kwh") is None
            else f"{computed['billing_kwh']:,.6f}"
        )
        alpha_text = (
            "N/A" if computed.get("alpha") is None else f"{computed['alpha']:.6g}"
        )
        silhouette = (
            cell["clusters"].get(kind, {}).get("diagnostics", {}).get("silhouette")
        )
        silhouette_text = "N/A" if silhouette is None else f"{silhouette:.4f}"
        self.statistics_model.set_records(
            [
                {"cluster_id": label, **statistics}
                for label, statistics in diagnostics.get("cluster_statistics", {})
                .get(kind, {})
                .items()
            ]
        )
        self.reconciliation_model.set_records(
            [
                {"customer_id": identifier, **values}
                for row in self.result.get("quality", [])
                if row["period"] == cell["year_month"]
                for identifier, values in row.get("cmis_reconciliation", {})
                .get("customers", {})
                .items()
            ]
        )
        self.summary.setText(
            f"Run {self.result['run_id'][:12]} · {self.result['status']} · {computed['status']} | "
            f"Mẫu chung: {diagnostics.get('cohort_size', 0)} KH · A: {billing_text} kWh · "
            f"α: {alpha_text} · cơ sở kỳ: {cell.get('billing_basis')} | silhouette: {silhouette_text}"
        )
        self.canvas.draw_idle()

    def _compare(
        self, cell, kind, target, unit, normalization, key, figure, records
    ) -> None:
        if self.result is None or self.comparison is None:
            return
        if not records:
            self.comparison_label.setText(
                "Run hiện tại thiếu đường cong cho lựa chọn này; chưa thể tính chênh lệch."
            )
            return
        other = next(
            (
                item
                for item in self.comparison["cells"]
                if item["industry_code"] == cell["industry_code"]
                and item["year_month"] == cell["year_month"]
            ),
            None,
        )
        changes = [
            name
            for name in sorted(
                set(self.result["config"]) | set(self.comparison["config"])
            )
            if self.result["config"].get(name) != self.comparison["config"].get(name)
        ]
        for name in ("calendar", "request", "software"):
            if self.result.get(name) != self.comparison.get(name):
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
        self.comparison_label.setText(
            f"So với run {self.comparison['run_id'][:12]} · tham số đổi: {', '.join(changes) or 'không'} · "
            f"mẫu chỉ ở run hiện tại: {len(current_ids - other_ids)}; chỉ ở run so sánh: {len(other_ids - current_ids)}"
        )
        if not other or kind not in other["result"][key]:
            self.comparison_label.setText(
                self.comparison_label.text() + " · không có đường cong tương ứng"
            )
            return
        try:
            vector = convert_curve(
                other["result"][key][kind],
                self.comparison["config"]["interval_minutes"],
                target,
                unit,
                normalization,
            )
        except ValueError:
            self.comparison_label.setText(
                self.comparison_label.text() + " · chọn độ phân giải thô hơn để so sánh"
            )
            return
        if vector is not None:
            figure.axes[0].plot(
                [index * target / 60 for index in range(len(vector))],
                vector,
                linestyle="--",
                color="#B04B2A",
                label="Run so sánh",
            )
            figure.axes[0].legend(fontsize=8)
            for row, value in zip(records, vector, strict=True):
                row["Run so sánh"] = float(value)
                row["Chênh lệch"] = row["Chung"] - float(value)

    def rename_dialog(self) -> None:
        cell, label = self.current_cell(), self.group.currentData()
        if cell is None or label is None:
            self.comparison_label.setText("Chọn một nhóm cụ thể trước khi đặt tên.")
            return
        name, accepted = QInputDialog.getText(
            self, "Tên nhóm hành vi", "Tên mô tả nghiệp vụ:"
        )
        if not accepted:
            return
        reason, accepted = QInputDialog.getText(
            self, "Cơ sở đặt tên", "Lý do/nguồn đối chiếu ca sản xuất:"
        )
        if accepted:
            self.rename_requested.emit(
                {
                    "industry": cell["industry_code"],
                    "period": cell["year_month"],
                    "day_type": self.day_type.currentData(),
                    "cluster_id": label,
                    "label": name,
                    "reason": reason,
                }
            )

    def inspect_dialog(self) -> None:
        cell = self.current_cell()
        if cell is None or self.result is None:
            return
        identifiers = {member["customer_id"] for member in cell["members"]}
        identifiers.update(
            identifier
            for row in self.result.get("quality", [])
            if row["period"] == cell["year_month"]
            for identifier in row.get("excluded", {})
        )
        if not identifiers:
            self.comparison_label.setText(
                "Không có khách hàng để kiểm tra trong ô này."
            )
            return
        customer_id, accepted = QInputDialog.getItem(
            self, "Kiểm tra ngày", "Mã khách hàng:", sorted(identifiers), editable=False
        )
        if accepted:
            day, accepted = QInputDialog.getText(
                self,
                "Kiểm tra ngày",
                "Ngày YYYY-MM-DD:",
                text=f"{cell['year_month']}-01",
            )
            if accepted:
                self.inspect_requested.emit(
                    {
                        "run_id": self.result["run_id"],
                        "customer_id": customer_id,
                        "date": day,
                    }
                )
