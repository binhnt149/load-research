"""Vietnamese research forms with explicit source semantics and column mapping."""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from load_research.application.models import SourceInput, StudyRequest
from load_research.calendar import ResearchCalendar
from load_research.domain.config import RunConfig, SourceOptions
from load_research.error_messages import format_error
from load_research.importers.tables import read_rows
from load_research.ui.source_preview import SourcePreviewDialog
from load_research.ui.template_dialog import TemplateDialog

CMIS_FIELDS = [
    "customer_id",
    "industry_code",
    "industry_name",
    "meter_id",
    "measurement_point_id",
    "organization_code",
    "valid_from",
    "valid_to",
    "meter_role",
    "sampling_weight",
    "annual_energy_kwh",
    "consumption_stratum",
    "year_month",
    "sample_billing_kwh",
    "sample_billing_basis",
]
BILLING_FIELDS = [
    "industry_code",
    "year_month",
    "billing_energy",
    "unit",
    "billing_basis",
    "organization_scope",
    "source_description",
]
MDMS_FIELDS = [
    "repair_blocked",
    "meter_id",
    "measurement_point_id",
    "timestamp",
    "interval_start",
    "interval_end",
    "value",
    "date",
    "customer_id",
    "organization_code",
    "channel",
    "source_quality_flag",
    "interval_minutes",
    "unit",
    "direction",
    "measurement_kind",
]


def combo(items: list[tuple[str, object]]) -> QComboBox:
    widget = QComboBox()
    for label, value in items:
        widget.addItem(label, value)
    return widget


def choose(widget: QComboBox, value: object) -> None:
    index = widget.findData(value)
    if index >= 0:
        widget.setCurrentIndex(index)


class FileList(QGroupBox):
    preview_requested = Signal(str)
    template_requested = Signal()

    def __init__(self, title: str) -> None:
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setObjectName("hint")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.list = QListWidget()
        self.list.setAccessibleName(title)
        self.list.setMaximumHeight(64)
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.list)
        buttons = QHBoxLayout()
        self.add_button, self.remove_button = (
            QPushButton("Thêm tệp…"),
            QPushButton("Bỏ lựa chọn"),
        )
        self.preview_button = QPushButton("Xem trước…")
        self.preview_button.clicked.connect(self.preview_current)
        self.list.itemDoubleClicked.connect(
            lambda item: self.preview_requested.emit(
                item.data(Qt.ItemDataRole.UserRole)
            )
        )
        self.list.currentItemChanged.connect(self.update_buttons)
        self.list.itemSelectionChanged.connect(self.update_buttons)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.preview_button)
        self.template_button = QPushButton("Tệp mẫu…")
        self.template_button.clicked.connect(lambda: self.template_requested.emit())
        buttons.addWidget(self.template_button)
        layout.addLayout(buttons)
        self.add_button.clicked.connect(self.select_files)
        self.remove_button.clicked.connect(self.remove_selected)
        self.update_buttons()

    def update_buttons(self, *_args) -> None:
        self.preview_button.setEnabled(self.list.currentItem() is not None)
        self.remove_button.setEnabled(bool(self.list.selectedItems()))
        count = self.list.count()
        self.summary.setText(
            f"{count} tệp đã thêm · double-click để xem trước"
            if count
            else "Chưa có tệp · chọn Thêm tệp để bắt đầu"
        )

    def current_path(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def preview_current(self) -> None:
        if path := self.current_path():
            self.preview_requested.emit(path)

    def paths(self) -> tuple[str, ...]:
        return tuple(
            self.list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.list.count())
        )

    def add_paths(self, paths) -> None:
        for path in paths:
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.list.addItem(item)

    def set_paths(self, paths) -> None:
        self.list.clear()
        self.add_paths(dict.fromkeys(str(path) for path in paths))
        if self.list.count():
            self.list.setCurrentRow(0)
        self.update_buttons()

    def select_files(self) -> None:
        paths, _filter = QFileDialog.getOpenFileNames(
            self, "Chọn tệp xuất hệ thống", "", "Dữ liệu (*.csv *.xlsx *.parquet)"
        )
        existing = set(self.paths())
        added = list(dict.fromkeys(path for path in paths if path not in existing))
        self.add_paths(added)
        if added:
            self.list.setCurrentRow(self.list.count() - 1)

    def remove_selected(self) -> None:
        row = self.list.currentRow()
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        if self.list.count():
            self.list.setCurrentRow(min(max(row, 0), self.list.count() - 1))
        self.update_buttons()


class ExportDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nội dung bộ báo cáo")
        layout = QFormLayout(self)
        self.layout_option = combo(
            [
                ("Bảng rộng: một đường cong mỗi dòng", "wide"),
                ("Bảng dài: một chu kỳ mỗi dòng", "long"),
            ]
        )
        layout.addRow("Cấu trúc CSV/XLSX", self.layout_option)
        self.xlsx, self.png, self.svg, self.members = [
            QCheckBox(text)
            for text in (
                "Kèm bảng Excel",
                "Hình PNG",
                "Hình SVG",
                "Kèm mã khách hàng/thành viên nhóm",
            )
        ]
        self.xlsx.setChecked(True)
        self.png.setChecked(True)
        self.timestamp_adjustments = QCheckBox(
            "Kèm nhật ký hiệu chỉnh và xung đột thời điểm trong kỳ nghiên cứu (có thể lớn)"
        )
        for checkbox in (
            self.xlsx,
            self.png,
            self.svg,
            self.members,
            self.timestamp_adjustments,
        ):
            layout.addRow(checkbox)
        layout.addRow(
            QLabel(
                "Bộ xuất luôn có CSV, phương pháp, chất lượng và manifest.\nĐơn vị/chu kỳ/chuẩn hoá theo lựa chọn đang hiển thị."
            )
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def options(self) -> dict:
        return {
            "layout": self.layout_option.currentData(),
            "include_xlsx": self.xlsx.isChecked(),
            "chart_formats": tuple(
                name
                for name, checkbox in (("png", self.png), ("svg", self.svg))
                if checkbox.isChecked()
            ),
            "include_members": self.members.isChecked(),
            "include_timestamp_adjustments": self.timestamp_adjustments.isChecked(),
        }


class CalendarDialog(QDialog):
    def __init__(self, calendar: ResearchCalendar, parent=None) -> None:
        super().__init__(parent)
        self.original = calendar
        self.setWindowTitle("Điều chỉnh lịch ngày nghiên cứu")
        self.resize(620, 450)
        layout = QVBoxLayout(self)
        note = QLabel(
            "Mỗi dòng: YYYY-MM-DD,day_type\nLoại ngày: weekday / saturday / sunday / holiday. Lịch tệp được áp sau các điều chỉnh này."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(
            "\n".join(
                f"{day.isoformat()},{kind.value}"
                for day, kind in sorted(calendar.overrides.items())
            )
        )
        layout.addWidget(self.editor)
        self.error = QLabel()
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> ResearchCalendar:
        from datetime import date

        from load_research.calendar import DayType

        overrides = {}
        for line in self.editor.toPlainText().splitlines():
            if line.strip():
                day, kind = (part.strip() for part in line.split(","))
                parsed = date.fromisoformat(day)
                if parsed in overrides:
                    raise ValueError("Một ngày chỉ được có một điều chỉnh.")
                overrides[parsed] = DayType(kind)
        return ResearchCalendar(set(self.original.holidays), overrides)

    def validate_and_accept(self) -> None:
        try:
            self.value()
        except ValueError as error:
            self.error.setText(format_error(error))
        else:
            self.accept()


class ColumnMappingDialog(QDialog):
    def __init__(
        self,
        path: str,
        fields: list[str],
        mapping: dict,
        *,
        sheet: str | None = None,
        delimiter: str = ",",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ánh xạ cột dữ liệu")
        self.resize(640, 520)
        reader = read_rows(Path(path), sheet=sheet, delimiter=delimiter)
        try:
            first = next(reader)
        finally:
            reader.close()
        headers = [key for key in first if not key.startswith("_")]
        layout = QVBoxLayout(self)
        label = QLabel(
            "Chọn cột nguồn tương ứng. Để trống trường không có; các trường bắt buộc được kiểm tra khi chạy."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.table = QTableWidget(len(fields), 2)
        self.table.setHorizontalHeaderLabels(["Trường chuẩn", "Cột trong tệp nguồn"])
        self.fields, self.selectors = fields, []
        for index, field in enumerate(fields):
            self.table.setCellWidget(index, 0, QLabel(field))
            selector = combo(
                [("— Không có —", "")] + [(header, header) for header in headers]
            )
            choose(selector, mapping.get(field, field))
            self.table.setCellWidget(index, 1, selector)
            self.selectors.append(selector)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 230)
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def mapping(self) -> dict[str, str]:
        return {
            field: selector.currentData()
            for field, selector in zip(self.fields, self.selectors, strict=True)
            if selector.currentData()
        }


class SourceDialog(QDialog):
    def __init__(self, path: str, options: SourceOptions, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ngữ nghĩa dữ liệu MDMS")
        self.path, self.original, self.mapping = path, options, dict(options.mapping)
        layout = QFormLayout(self)
        filename = QLabel(Path(path).name)
        filename.setWordWrap(True)
        layout.addRow(filename)
        self.minutes = combo([(f"{n} phút", n) for n in (15, 30, 60)])
        self.kind = combo(
            [
                ("Điện năng trong chu kỳ", "interval_energy"),
                ("Công suất trung bình chu kỳ", "interval_average_power"),
            ]
        )
        self.unit = combo(
            [(unit, unit) for unit in ("Wh", "kWh", "MWh", "W", "kW", "MW")]
        )
        self.stamp = combo([("Đầu chu kỳ", "start"), ("Cuối chu kỳ", "end")])
        self.alignment = combo(
            [
                ("Về đầu khoảng theo chu kỳ nguồn", "floor"),
                ("Từ chối thời điểm lệch biên", "strict"),
            ]
        )
        self.layout_type = combo(
            [
                ("Dạng dài: thời điểm / giá trị", "long"),
                ("Dạng rộng: một hàng / ngày", "wide"),
            ]
        )
        self.scaled = QCheckBox("Nguồn đã áp dụng hệ số công tơ")
        self.multiplier = QDoubleSpinBox()
        self.multiplier.setDecimals(6)
        self.multiplier.setRange(0.000001, 1e9)
        self.sheet = QLineEdit(options.sheet or "")
        self.delimiter = QLineEdit(options.delimiter)
        self.delimiter.setMaxLength(1)
        self.decimal = combo([("Dấu chấm", "."), ("Dấu phẩy", ",")])
        self.timestamp_format = QLineEdit(options.timestamp_format or "")
        self.timestamp_format.setPlaceholderText(
            "Trống: ISO 8601; ví dụ khác: %d/%m/%Y %H:%M"
        )
        self.slot_prefix = QLineEdit(options.slot_prefix)
        for widget, value in (
            (self.minutes, options.interval_minutes),
            (self.kind, options.measurement_kind),
            (self.unit, options.unit),
            (self.stamp, options.timestamp_convention),
            (self.alignment, options.timestamp_alignment),
            (self.layout_type, options.layout),
            (self.decimal, options.decimal),
        ):
            choose(widget, value)
        self.scaled.setChecked(bool(options.values_already_scaled))
        self.multiplier.setValue(options.multiplier)
        for label, source_widget in (
            ("Chu kỳ nguồn", self.minutes),
            ("Đại lượng", self.kind),
            ("Đơn vị nguồn", self.unit),
            ("Dấu thời gian", self.stamp),
            ("Hiệu chỉnh thời điểm", self.alignment),
            ("Cấu trúc", self.layout_type),
            ("Hệ số", self.multiplier),
            ("Sheet Excel (trống: đầu tiên)", self.sheet),
            ("Dấu phân cách CSV", self.delimiter),
            ("Dấu thập phân", self.decimal),
            ("Định dạng thời gian", self.timestamp_format),
            ("Tiền tố cột chu kỳ (slot_01…)", self.slot_prefix),
        ):
            layout.addRow(label, source_widget)
        layout.addRow(self.scaled)
        mapping_button = QPushButton("Ánh xạ cột…")
        mapping_button.clicked.connect(self.edit_mapping)
        layout.addRow(mapping_button)
        self.error = QLabel()
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        self.error.setWordWrap(True)
        layout.addRow(self.error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def edit_mapping(self) -> None:
        fields = MDMS_FIELDS + [
            f"{self.slot_prefix.text()}{index:02}"
            for index in range(1, 1440 // self.minutes.currentData() + 1)
        ]
        try:
            dialog = ColumnMappingDialog(
                self.path,
                fields,
                self.mapping,
                sheet=self.sheet.text() or None,
                delimiter=self.delimiter.text(),
                parent=self,
            )
            if dialog.exec():
                self.mapping = dialog.mapping()
        except (ValueError, OSError, StopIteration) as error:
            self.error.setText(format_error(error))

    def value(self) -> SourceOptions:
        return replace(
            self.original,
            values_already_scaled=self.scaled.isChecked(),
            multiplier=self.multiplier.value(),
            interval_minutes=self.minutes.currentData(),
            measurement_kind=self.kind.currentData(),
            unit=self.unit.currentData(),
            timestamp_convention=self.stamp.currentData(),
            timestamp_alignment=self.alignment.currentData(),
            layout=self.layout_type.currentData(),
            mapping=self.mapping,
            sheet=self.sheet.text() or None,
            delimiter=self.delimiter.text(),
            decimal=self.decimal.currentData(),
            timestamp_format=self.timestamp_format.text() or None,
            slot_prefix=self.slot_prefix.text(),
        )

    def validate_and_accept(self) -> None:
        try:
            self.value()
        except ValueError as error:
            self.error.setText(format_error(error))
        else:
            self.accept()


class ConfigForm(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("configForm")
        self.base = RunConfig(periods=("2026-01",), scope="NPC")
        layout = QFormLayout(self)
        self.scope, self.periods = QLineEdit(), QLineEdit()
        self.periods.setPlaceholderText("2026-01,2026-02,…")
        self.timezone = QLineEdit()
        self.resolution = combo(
            [("48 chu kỳ / 30 phút", 30), ("24 chu kỳ / 60 phút", 60)]
        )
        self.algorithm = combo([("K-Means", "kmeans"), ("DBSCAN", "dbscan")])
        self.vee_completion = combo(
            [
                ("Bù đủ khi có căn cứ; loại mẫu còn thiếu", "complete"),
                ("Quy tắc cũ: bù có giới hạn", "legacy"),
            ]
        )
        self.collision_policy = combo(
            [
                ("Ưu tiên thời điểm gần đầu chu kỳ; ghi nhật ký", "prefer_nearest"),
                ("Dừng khi số liệu trùng khác nhau", "reject"),
            ]
        )
        for label, widget in (
            ("Phạm vi đơn vị", self.scope),
            ("Năm-tháng (cách nhau bằng dấu phẩy)", self.periods),
            ("Múi giờ", self.timezone),
            ("Độ phân giải phân tích", self.resolution),
            ("Thuật toán", self.algorithm),
            ("Hoàn chỉnh dữ liệu VEE", self.vee_completion),
            ("Xử lý số liệu trùng chu kỳ", self.collision_policy),
        ):
            layout.addRow(label, widget)
        integer_labels = {
            "max_linear_minutes": "Khoảng nội suy tối đa (phút)",
            "max_like_minutes": "Khoảng ngày tương đồng tối đa (phút)",
            "min_donors": "Số ngày nguồn tối thiểu",
            "min_customers": "Số khách hàng chung tối thiểu",
            "min_cluster_customers": "Số vector dương tối thiểu để phân cụm",
            "k_min": "Số cụm nhỏ nhất",
            "k_max": "Số cụm lớn nhất",
            "n_init": "Số lần khởi tạo K-Means",
            "max_iter": "Số vòng lặp tối đa",
            "silhouette_sample": "Số mẫu tính silhouette",
            "min_cluster_size": "Số khách hàng tối thiểu/cụm",
            "min_samples": "Số mẫu lân cận tối thiểu DBSCAN",
            "max_dbscan_vectors": "Giới hạn vector DBSCAN",
            "memory_limit_mb": "Bộ nhớ truy vấn tối đa (MB)",
            "worker_threads": "Số luồng tính toán",
            "mad_min_days": "Số ngày gốc tối thiểu để cảnh báo MAD",
        }
        self.integers: dict[str, QSpinBox] = {}
        for name, label in integer_labels.items():
            integer_widget = QSpinBox()
            integer_widget.setRange(0 if name.startswith("max_") else 1, 1_000_000)
            layout.addRow(label, integer_widget)
            self.integers[name] = integer_widget
        self.fractions: dict[str, QDoubleSpinBox] = {}
        labels = {
            "max_estimated_fraction": "Tỷ lệ chu kỳ ước lượng tối đa/ngày",
            "min_original_coverage": "Độ phủ gốc tối thiểu/tháng",
            "silhouette_min": "Silhouette tối thiểu",
            "silhouette_tie": "Ngưỡng hoà silhouette",
            "min_cluster_fraction": "Tỷ lệ khách hàng tối thiểu/cụm",
            "donor_common_fraction": "Tỷ lệ chu kỳ quan sát chung tối thiểu khi bù",
        }
        for name, label in labels.items():
            fraction_widget = QDoubleSpinBox()
            fraction_widget.setRange(0, 1)
            fraction_widget.setDecimals(4)
            fraction_widget.setSingleStep(0.01)
            layout.addRow(label, fraction_widget)
            self.fractions[name] = fraction_widget
        self.parameters: dict[str, QDoubleSpinBox] = {}
        for name, label in (
            ("donor_scale_min", "Hệ số bù ngày tương đồng nhỏ nhất"),
            ("donor_scale_max", "Hệ số bù ngày tương đồng lớn nhất"),
            ("mad_factor", "Hệ số MAD (chỉ cảnh báo)"),
        ):
            parameter = QDoubleSpinBox()
            parameter.setRange(0.001, 1_000_000)
            parameter.setDecimals(3)
            layout.addRow(label, parameter)
            self.parameters[name] = parameter
        self.manual_k = QSpinBox()
        self.manual_k.setRange(0, 50)
        self.manual_k.setSpecialValueText("Tự chọn số cụm")
        self.eps, self.seed = QLineEdit(), QLineEdit()
        layout.addRow("Số cụm đặt tay (0 = tự động)", self.manual_k)
        layout.addRow("Bán kính lân cận DBSCAN (bắt buộc)", self.eps)
        layout.addRow("Hạt giống ngẫu nhiên để tái lập", self.seed)
        self.minimum_days = []
        for label in ("ngày làm việc", "thứ Bảy", "Chủ nhật", "ngày lễ"):
            days_widget = QSpinBox()
            days_widget.setRange(1, 31)
            layout.addRow(f"Ngày dùng tối thiểu: {label}", days_widget)
            self.minimum_days.append(days_widget)
        self.set_config(self.base)
        defaults = QPushButton("Khôi phục tham số mặc định đề xuất")
        defaults.clicked.connect(
            lambda: self.set_config(
                RunConfig(
                    periods=self.value().periods,
                    scope=self.value().scope,
                    timezone=self.value().timezone,
                )
            )
        )
        layout.addRow(defaults)
        method = QLabel(
            "Phương pháp: M = trung bình ngày của từng KH; F = Σ(w×M); S = Σ(N×ΣF); α = A/S; E = αF; P = E/Δt.\n"
            "Q = F/ΣF; U = K×Q; V = F/max(F). Bù có giới hạn; MAD chỉ cảnh báo. Phân cụm dùng Q và giữ cả noise trong tổng."
        )
        method.setWordWrap(True)
        layout.addRow(method)

    def set_config(self, config: RunConfig) -> None:
        self.base = config
        self.scope.setText(config.scope)
        self.periods.setText(",".join(config.periods))
        self.timezone.setText(config.timezone)
        choose(self.resolution, config.interval_minutes)
        choose(self.algorithm, config.algorithm)
        choose(self.vee_completion, config.vee_completion)
        choose(self.collision_policy, config.collision_policy)
        for name, widget in self.numeric_controls().items():
            widget.setValue(getattr(config, name))
        self.manual_k.setValue(config.manual_k or 0)
        self.eps.setText(str(config.eps) if config.eps is not None else "")
        self.seed.setText(str(config.seed))
        for widget, value in zip(self.minimum_days, config.min_days, strict=True):
            widget.setValue(value)

    def value(self) -> RunConfig:
        payload = self.base.to_dict()
        payload.update(
            periods=[
                item.strip() for item in self.periods.text().split(",") if item.strip()
            ],
            scope=self.scope.text().strip(),
            timezone=self.timezone.text().strip(),
            interval_minutes=self.resolution.currentData(),
            algorithm=self.algorithm.currentData(),
            vee_completion=self.vee_completion.currentData(),
            collision_policy=self.collision_policy.currentData(),
            manual_k=self.manual_k.value() or None,
            eps=float(self.eps.text()) if self.eps.text().strip() else None,
            seed=int(self.seed.text()),
            min_days=[widget.value() for widget in self.minimum_days],
        )
        payload.update(
            {name: widget.value() for name, widget in self.numeric_controls().items()}
        )
        return RunConfig.from_dict(payload)

    def numeric_controls(self) -> dict[str, QSpinBox | QDoubleSpinBox]:
        return {**self.integers, **self.fractions, **self.parameters}


class ResearchForm(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("researchForm")
        self.base_calendar = ResearchCalendar()
        self.source_options: dict[str, SourceOptions] = {}
        self.cmis_mapping: dict[str, str] = {}
        self.billing_mapping: dict[str, str] = {}
        self.selected_industries: tuple[str, ...] = ()
        layout = QVBoxLayout(self)
        sources = QGridLayout()
        sources.setHorizontalSpacing(16)
        sources.setVerticalSpacing(12)
        sources.setColumnStretch(0, 1)
        sources.setColumnStretch(1, 1)
        self.cmis, self.mdms, self.billing, self.calendar_files, self.strata = [
            FileList(title)
            for title in (
                "1. CMIS — tập khách hàng mẫu đã chốt",
                "2. MDMS — dữ liệu đo chu kỳ",
                "3. Điện năng thương phẩm toàn ngành",
                "4. Lịch ngày đặc biệt (tuỳ chọn)",
                "5. Cấu hình nhóm sản lượng (tuỳ chọn)",
            )
        ]
        for index, (selector, category) in enumerate(
            zip(
                (self.cmis, self.mdms, self.billing, self.calendar_files, self.strata),
                ("cmis", "mdms", "billing", "calendar", "strata"),
                strict=True,
            )
        ):
            sources.addWidget(selector, index // 2, index % 2)
            selector.preview_requested.connect(
                lambda path, s=selector: self.preview_source(s, path)
            )
            selector.template_requested.connect(
                lambda c=category: TemplateDialog(category=c, parent=self).exec()
            )
        layout.addLayout(sources)
        actions = QHBoxLayout()
        calendar_button = QPushButton("Điều chỉnh lịch trực tiếp…")
        calendar_button.clicked.connect(self.edit_calendar)
        source_button = QPushButton("Thiết lập ngữ nghĩa / ánh xạ MDMS đang chọn…")
        source_button.clicked.connect(self.edit_source)
        actions.addWidget(source_button)
        actions.addWidget(calendar_button)
        layout.addLayout(actions)
        self.options_toggle = QToolButton()
        self.options_toggle.setText(
            "Thiết lập cột & định dạng CMIS / thương phẩm / lịch"
        )
        self.options_toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.options_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.options_toggle.setCheckable(True)
        layout.addWidget(self.options_toggle)
        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        self.options_toggle.toggled.connect(advanced.setVisible)
        self.options_toggle.toggled.connect(
            lambda checked: self.options_toggle.setArrowType(
                Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
            )
        )
        advanced.hide()
        layout.addWidget(advanced)
        self.cmis_sheet, self.billing_sheet, self.table_delimiter = (
            QLineEdit(),
            QLineEdit(),
            QLineEdit(","),
        )
        options = QFormLayout()
        options.addRow("Sheet CMIS (trống: đầu tiên)", self.cmis_sheet)
        options.addRow("Trang tính thương phẩm", self.billing_sheet)
        options.addRow("Dấu phân cách CMIS/thương phẩm/lịch", self.table_delimiter)
        self.meter_key_policy = combo(
            [
                ("Bỏ khoảng trắng, ưu tiên mã công tơ", "trimmed"),
                ("Quy tắc ghép cũ", "legacy"),
            ]
        )
        options.addRow("Quy tắc ghép mã công tơ/điểm đo", self.meter_key_policy)
        advanced_layout.addLayout(options)
        mapping_buttons = QHBoxLayout()
        for selector, fields, name, label in (
            (self.cmis, CMIS_FIELDS, "cmis_mapping", "Ánh xạ cột CMIS…"),
            (
                self.billing,
                BILLING_FIELDS,
                "billing_mapping",
                "Ánh xạ cột thương phẩm…",
            ),
        ):
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, s=selector, f=fields, n=name: (
                    self.edit_table_mapping(s, f, n)
                )
            )
            mapping_buttons.addWidget(button)
        advanced_layout.addLayout(mapping_buttons)
        note = QLabel(
            "MDMS: khai báo đúng đơn vị, chu kỳ và hệ số trước khi chạy. "
            "Dùng “Tệp mẫu…” để xem cấu trúc đầu vào."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        layout.addWidget(note)
        layout.addStretch(1)
        self.config_form = ConfigForm()

    def set_request(self, request: StudyRequest) -> None:
        choose(self.meter_key_policy, request.meter_key_policy)
        self.config_form.set_config(request.config)
        self.cmis.set_paths(request.cmis_paths)
        self.mdms.set_paths(source.path for source in request.mdms_sources)
        self.billing.set_paths(request.billing_paths)
        self.calendar_files.set_paths(request.calendar_paths)
        self.strata.set_paths(request.strata_paths)
        self.source_options = {
            source.path: source.options for source in request.mdms_sources
        }
        self.cmis_mapping, self.billing_mapping = (
            dict(request.cmis_mapping),
            dict(request.billing_mapping),
        )
        self.base_calendar, self.selected_industries = (
            request.calendar,
            request.selected_industries,
        )
        self.cmis_sheet.setText(request.cmis_sheet or "")
        self.billing_sheet.setText(request.billing_sheet or "")
        self.table_delimiter.setText(request.table_delimiter)

    def build_request(self) -> StudyRequest:
        config = self.config_form.value()
        if any(path not in self.source_options for path in self.mdms.paths()):
            raise ValueError(
                "Hãy khai báo ngữ nghĩa/ánh xạ từng tệp MDMS trước khi chạy."
            )
        sources = tuple(
            SourceInput(path, self.source_options[path]) for path in self.mdms.paths()
        )
        return StudyRequest(
            config,
            self.cmis.paths(),
            sources,
            self.billing.paths(),
            self.base_calendar,
            self.calendar_files.paths(),
            self.cmis_mapping,
            self.billing_mapping,
            self.cmis_sheet.text() or None,
            self.billing_sheet.text() or None,
            self.table_delimiter.text(),
            self.selected_industries,
            self.meter_key_policy.currentData(),
            self.strata.paths(),
        )

    def edit_source(self) -> None:
        path = self.mdms.current_path()
        if path is None:
            return
        dialog = SourceDialog(
            path,
            self.source_options.get(path, SourceOptions(values_already_scaled=True)),
            self,
        )
        if dialog.exec():
            self.source_options[path] = dialog.value()

    def preview_source(self, selector: FileList, path: str) -> None:
        try:
            sheet, delimiter = None, self.table_delimiter.text()
            if selector is self.mdms:
                options = self.source_options.get(
                    path, SourceOptions(values_already_scaled=True)
                )
                sheet, delimiter = options.sheet, options.delimiter
            elif selector is self.cmis:
                sheet = self.cmis_sheet.text() or None
            elif selector is self.billing:
                sheet = self.billing_sheet.text() or None
            SourcePreviewDialog(
                path, sheet=sheet, delimiter=delimiter, parent=self
            ).exec()
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Không đọc được nguồn", format_error(error))

    def edit_calendar(self) -> None:
        dialog = CalendarDialog(self.base_calendar, self)
        if dialog.exec():
            self.base_calendar = dialog.value()

    def edit_table_mapping(
        self, selector: FileList, fields: list[str], name: str
    ) -> None:
        if not selector.paths():
            return
        try:
            sheet = (
                self.cmis_sheet.text()
                if name == "cmis_mapping"
                else self.billing_sheet.text()
            )
            dialog = ColumnMappingDialog(
                selector.paths()[0],
                fields,
                getattr(self, name),
                sheet=sheet or None,
                delimiter=self.table_delimiter.text(),
                parent=self,
            )
            if dialog.exec():
                setattr(self, name, dialog.mapping())
        except (ValueError, OSError, StopIteration) as error:
            QMessageBox.warning(self, "Không đọc được cột", format_error(error))
