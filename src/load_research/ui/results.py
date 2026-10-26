"""Computed curve filters, quality, cohort comparison and cluster display labels."""

from dataclasses import asdict

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from load_research.calendar import ResearchCalendar, month_days
from load_research.error_messages import format_error, import_issue_rows
from load_research.exports import apply_annotations, cluster_display_name, convert_curve
from load_research.presentation import DAY_TYPES, field_label, format_value
from load_research.result_reporting import interval_records, render_view
from load_research.result_view import (
    ResultSelection,
    build_daily_view,
    build_result_view,
)
from load_research.ui.forms import choose, combo
from load_research.ui.models import RecordsModel
from load_research.ui.result_controls import MultiSelectCombo, chart_point_text


class ResultsView(QWidget):
    rename_requested = Signal(dict)
    export_requested = Signal(bool)
    inspect_requested = Signal(dict)
    daily_requested = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.result: dict | None = None
        self.comparison: dict | None = None
        self.annotations: list[dict] = []
        self.daily_data: dict = {}
        self.current_view: dict | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        self.summary = QLabel("Chưa có kết quả")
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        filters = QHBoxLayout()
        self.industry, self.day_type = MultiSelectCombo(), MultiSelectCombo()
        self.period, self.group = QComboBox(), QComboBox()
        for label, filter_widget in (
            ("Ngành", self.industry),
            ("Tháng", self.period),
            ("Loại ngày", self.day_type),
            ("Nhóm", self.group),
        ):
            filters.addWidget(QLabel(label))
            filters.addWidget(filter_widget, 1)
        layout.addLayout(filters)
        aggregation = QHBoxLayout()
        self.level = combo(
            [
                ("Ngành đã chọn", "industries"),
                ("Thành phần phụ tải", "component"),
                ("Toàn đơn vị", "organization"),
            ]
        )
        self.component_name = QLineEdit()
        self.component_name.setPlaceholderText("Tên thành phần phụ tải")
        self.mode = combo(
            [("Ngày đại diện", "representative"), ("Theo từng ngày", "daily")]
        )
        widget: QWidget
        for widget in (self.level, self.component_name, self.mode):
            aggregation.addWidget(widget, 1)
        layout.addLayout(aggregation)
        self.daily_row = QWidget()
        daily_layout = QHBoxLayout(self.daily_row)
        daily_layout.setContentsMargins(0, 0, 0, 0)
        self.date = QComboBox()
        self.daily_method = combo(
            [
                ("Đại diện theo loại ngày", "representative"),
                ("Giữ biến thiên ngày, hệ số tháng riêng", "variation"),
            ]
        )
        self.load_daily_button = QPushButton("Nạp dữ liệu ngày")
        self.load_daily_button.clicked.connect(self.request_daily)
        for widget in (self.date, self.daily_method, self.load_daily_button):
            daily_layout.addWidget(widget, 1)
        layout.addWidget(self.daily_row)
        self.daily_row.hide()
        options = QHBoxLayout()
        self.resolution = combo([("48 chu kỳ", 30), ("24 chu kỳ", 60)])
        self.unit = combo([("Công suất kW", "kW"), ("Điện năng kWh", "kWh")])
        self.scope = combo(
            [
                ("Phụ tải suy rộng", "industry_scaled"),
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
        self.comparison_label.hide()
        layout.addWidget(self.comparison_label)
        self.point_label = QLabel("Bấm biểu đồ để xem số liệu chu kỳ.")
        self.point_label.setTextFormat(Qt.TextFormat.PlainText)
        self.point_label.setWordWrap(True)
        self.point_label.setMaximumHeight(44)
        point_row = QHBoxLayout()
        point_row.addWidget(self.point_label, 1)
        self.table_toggle = QToolButton()
        self.table_toggle.setText("Bảng")
        self.table_toggle.setAccessibleName("Mở rộng bảng số liệu")
        self.table_toggle.setToolTip(
            "Ẩn/hiện biểu đồ để mở rộng bảng số liệu trên cửa sổ nhỏ"
        )
        point_row.addWidget(self.table_toggle)
        layout.addLayout(point_row)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.canvas = FigureCanvasQTAgg(Figure(figsize=(10, 4)))
        self.canvas.setMinimumHeight(180)
        self.table_toggle.clicked.connect(
            lambda: self.canvas.setVisible(not self.canvas.isVisible())
        )
        self.canvas.mpl_connect("button_press_event", self.show_chart_point)
        splitter.addWidget(self.canvas)
        tabs = QTabWidget()
        tabs.setUsesScrollButtons(True)
        tabs.setElideMode(Qt.TextElideMode.ElideRight)
        tabs.tabBar().setExpanding(False)
        tabs.setMinimumHeight(32)
        splitter.setChildrenCollapsible(False)
        (
            self.table_model,
            self.quality_model,
            self.members_model,
            self.excluded_model,
        ) = [RecordsModel(self) for _ in range(4)]
        self.factors_model, self.missing_model = RecordsModel(self), RecordsModel(self)
        self.import_model = RecordsModel(self)
        self.statistics_model, self.reconciliation_model = (
            RecordsModel(self),
            RecordsModel(self),
        )
        for label, model in (
            ("Chu kỳ", self.table_model),
            ("Hệ số suy rộng", self.factors_model),
            ("Dữ liệu còn thiếu", self.missing_model),
            ("Nhập MDMS toàn đợt (tối đa 1.000 lỗi)", self.import_model),
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
        help_button = QPushButton("Cách tính…")
        help_button.clicked.connect(self.show_methodology)
        buttons.addWidget(help_button)
        layout.addLayout(buttons)
        self.industry.selectionChanged.connect(self.refresh_periods)
        self.day_type.selectionChanged.connect(self.refresh_dates)
        self.level.currentIndexChanged.connect(self.render_results)
        self.component_name.textChanged.connect(self.render_results)
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.date.currentIndexChanged.connect(self.render_results)
        self.daily_method.currentIndexChanged.connect(self.render_results)
        self.industry.currentIndexChanged.connect(self.refresh_periods)
        self.period.currentIndexChanged.connect(self.refresh_days)
        self.day_type.currentIndexChanged.connect(self.refresh_dates)
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
        for control in self.findChildren(QComboBox):
            control.setMinimumContentsLength(8)
            control.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )

    @staticmethod
    def fill(widget: QComboBox, items: list[tuple[str, object]]) -> None:
        old = widget.currentData()
        previous = (
            widget.selected_data() if isinstance(widget, MultiSelectCombo) else ()
        )
        widget.blockSignals(True)
        widget.clear()
        for label, value in items:
            widget.addItem(label, value)
        choose(widget, old)
        if isinstance(widget, MultiSelectCombo) and widget.count():
            selected = tuple(value for value in previous if widget.findData(value) >= 0)
            widget.set_selected(selected or (widget.currentData(),))
        widget.blockSignals(False)

    def set_result(self, result: dict, annotations: list[dict] | None = None) -> None:
        self.result, self.annotations, self.comparison = result, annotations or [], None
        self.daily_data = {}
        self.current_view = None
        self.import_model.set_records(import_issue_rows(result))
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
            "industry_codes": self.industry.selected_data() if selected else (),
            "periods": (self.period.currentData(),) if selected else (),
            "day_types": self.day_type.selected_data() if selected else (),
            "view_selection": asdict(self.selection())
            if selected
            else {
                **asdict(self.selection()),
                "industry_codes": (),
                "day_types": (),
                "period": "",
                "level": "organization",
                "name": "",
            },
            "daily_method": self.daily_method.currentData()
            if self.mode.currentData() == "daily"
            else None,
            "dates": (self.date.currentData(),)
            if selected and self.mode.currentData() == "daily"
            else (),
            "cluster_ids": (self.group.currentData(),)
            if selected and self.group.isEnabled() and self.group.currentData()
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
                    if cell["industry_code"] in self.industry.selected_data()
                }
            )
            self.fill(self.period, [(period, period) for period in periods])
            self.refresh_days()

    def refresh_days(self) -> None:
        cell = self.current_cell()
        if cell:
            labels = DAY_TYPES
            self.fill(
                self.day_type,
                [
                    (labels[kind], kind)
                    for kind in ("weekday", "saturday", "sunday", "holiday")
                    if cell["day_counts"].get(kind, 0)
                ],
            )
        self.daily_data = {}
        self.refresh_dates()

    def refresh_dates(self) -> None:
        if self.result and self.period.currentData():
            calendar = ResearchCalendar.from_dict(self.result.get("calendar", {}))
            self.fill(
                self.date,
                [
                    (day.isoformat(), day.isoformat())
                    for day in month_days(self.period.currentData())
                    if not self.day_type.selected_data()
                    or calendar.classify(day).value in self.day_type.selected_data()
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

    def selection(self) -> ResultSelection:
        return ResultSelection(
            self.period.currentData(),
            self.industry.selected_data(),
            self.day_type.selected_data(),
            interval_minutes=self.resolution.currentData(),
            unit=self.unit.currentData(),
            scope=self.scope.currentData(),
            normalization=self.normalization.currentData(),
            level=self.level.currentData(),
            name=self.component_name.text().strip()
            if self.level.currentData() == "component"
            else "",
        )

    def change_mode(self) -> None:
        self.daily_row.setVisible(self.mode.currentData() == "daily")
        self.render_results()

    def request_daily(self) -> None:
        if self.result and self.period.currentData():
            self.daily_requested.emit(
                {
                    "run_id": self.result["run_id"],
                    "period": self.period.currentData(),
                    "codes": ()
                    if self.level.currentData() == "organization"
                    else self.industry.selected_data(),
                }
            )

    def set_daily_data(self, data: dict) -> None:
        self.daily_data = data
        self.render_results()

    def show_chart_point(self, event) -> None:
        if self.current_view:
            text = chart_point_text(
                event,
                self.canvas,
                minutes=self.current_view["interval_minutes"],
                unit=self.current_view["unit"],
            )
            if text:
                self.point_label.setText(text)
                self.point_label.setToolTip(text)

    def show_methodology(self) -> None:
        from load_research.methodology import CALCULATIONS

        dialog = QDialog(self)
        dialog.setWindowTitle("Phương pháp tính kết quả")
        dialog.resize(850, 650)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setMarkdown(CALCULATIONS)
        layout.addWidget(browser)
        dialog.exec()

    def render_results(self) -> None:
        self.point_label.setText("Bấm biểu đồ để xem số liệu chu kỳ.")
        self.point_label.setToolTip("")
        cell, kind = self.current_cell(), self.day_type.currentData()
        if self.result is None or cell is None or kind is None:
            return
        selection = self.selection()
        self.component_name.setEnabled(selection.level == "component")
        self.industry.setEnabled(selection.level != "organization")
        self.stacked.setEnabled(selection.normalization is None)
        self.group.setEnabled(
            selection.level != "organization"
            and len(self.industry.selected_data()) == 1
            and len(self.day_type.selected_data()) == 1
            and self.mode.currentData() != "daily"
        )
        try:
            if self.mode.currentData() == "daily":
                if not self.daily_data or not self.date.currentData():
                    self.canvas.figure.clear()
                    self.canvas.draw_idle()
                    self.table_model.set_records([])
                    self.current_view = None
                    self.summary.setText(
                        "Chọn Nạp dữ liệu ngày để đọc tập mẫu đã lưu trong tiến trình nền."
                    )
                    return
                view = build_daily_view(
                    self.named_result(),
                    selection,
                    self.daily_data,
                    self.date.currentData(),
                    method=self.daily_method.currentData(),
                )
            else:
                view = build_result_view(self.named_result(), selection)
            self.current_view = view
            self.factors_model.set_records(view.get("daily_factors", view["factors"]))
            self.missing_model.set_records(view["missing"])
            families = (
                ("industry", "day_type", "behavior", "source", "processed", "expanded")
                if self.components.isChecked()
                else ()
            )
            if self.group.isEnabled() and self.group.currentData():
                view = {
                    **view,
                    "series": [
                        row
                        for row in view["series"]
                        if row["kind"] != "behavior"
                        or row.get("cluster_id") == self.group.currentData()
                    ],
                }
            figure = render_view(
                view,
                figure=self.canvas.figure,
                families=families,
                stacked=self.stacked.isChecked(),
            )
            records = interval_records(view)
        except (ValueError, KeyError, TypeError) as error:
            self.current_view = None
            self.table_model.set_records([])
            self.canvas.figure.clear()
            self.canvas.draw_idle()
            self.summary.setText(format_error(error))
            return
        self.comparison_label.setText("")
        key = "sample" if selection.scope == "sample_portfolio" else "energy"
        if (
            self.comparison
            and len(view["industry_codes"]) == len(view["day_types"]) == 1
            and self.mode.currentData() != "daily"
        ):
            self._compare(
                cell,
                kind,
                selection.interval_minutes,
                selection.unit,
                selection.normalization,
                key,
                figure,
                records,
            )
        elif self.comparison:
            self.comparison_label.setText(
                "So sánh lần chạy: chọn một ngành và một loại ngày."
            )
        self.comparison_label.setVisible(bool(self.comparison_label.text()))
        self.table_model.set_records(records)
        cells = [
            item
            for item in self.named_result()["cells"]
            if item["year_month"] == selection.period
            and item["industry_code"] in view["industry_codes"]
        ]
        quality = [
            row
            for row in self.result.get("quality", [])
            if row["period"] == selection.period
        ]
        self.quality_model.set_records(
            [
                {
                    key: value
                    for key, value in row.items()
                    if isinstance(value, (str, int, float))
                }
                for row in quality
            ]
        )
        self.members_model.set_records(
            [
                {"industry_code": item["industry_code"], **member}
                for item in cells
                for member in item["members"]
                if member["day_type"] in view["day_types"]
            ]
        )
        self.excluded_model.set_records(
            [
                {"customer_id": identifier, "reason": reason}
                for row in quality
                for identifier, reason in row.get("excluded", {}).items()
            ]
        )
        self.statistics_model.set_records(
            [
                {
                    "industry_code": item["industry_code"],
                    "day_type": day_type,
                    "cluster_id": label,
                    **statistics,
                }
                for item in cells
                for day_type, groups in item["result"]["diagnostics"]
                .get("cluster_statistics", {})
                .items()
                if day_type in view["day_types"]
                for label, statistics in groups.items()
            ]
        )
        self.reconciliation_model.set_records(
            [
                {"customer_id": identifier, **values}
                for row in quality
                for identifier, values in row.get("cmis_reconciliation", {})
                .get("customers", {})
                .items()
            ]
        )
        self.summary.setText(
            f"{len(view['industry_codes'])} ngành · {view['day_count']} ngày · "
            f"Điện năng lựa chọn: {format_value('value', view['energy_selected_kwh'])} kWh · "
            f"Thương phẩm tháng: {format_value('value', view['billing_kwh'])} kWh · "
            + ("Đủ đường tổng hợp" if view["complete"] else "Chưa đủ đường tổng hợp")
            + f" · {sum(item['result']['status'] not in ('valid', 'valid_with_warnings') for item in cells)} ngành cần xem trạng thái mẫu"
        )
        self.canvas.draw_idle()

    def _compare(
        self, cell, kind, target, unit, normalization, key, figure, records
    ) -> None:
        if self.result is None or self.comparison is None:
            return
        if not records or records[0].get("Chung") is None:
            self.comparison_label.setText(
                "Lần hiện tại thiếu đường cong cho lựa chọn này; chưa thể tính chênh lệch."
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
            f"So với lần nghiên cứu {self.comparison['run_id'][:12]} · tham số đổi: {', '.join(f'{field_label(name)} ({name})' for name in changes) or 'không'} · "
            f"mẫu chỉ ở lần hiện tại: {len(current_ids - other_ids)}; chỉ ở lần so sánh: {len(other_ids - current_ids)}"
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
                label="Lần so sánh",
            )
            figure.axes[0].legend(fontsize=8)
            for row, value in zip(records, vector, strict=True):
                row["Lần so sánh"] = float(value)
                row["Chênh lệch"] = row["Chung"] - float(value)

    def rename_dialog(self) -> None:
        cell, label = self.current_cell(), self.group.currentData()
        if cell is None or label is None or not self.group.isEnabled():
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
