"""A bounded, read-only explanation of one customer's day."""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTableView, QVBoxLayout

from load_research.ui.models import RecordsModel


class DayInspectionDialog(QDialog):
    def __init__(self, details: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Giải thích dữ liệu trước / sau bù")
        self.resize(1000, 750)
        layout = QVBoxLayout(self)
        heading = QLabel(
            f"KH {details['customer_id']} · {details['date']} · {details['day_type']} · run {details['run_id'][:12]}\n"
            f"Ngày đủ điều kiện: {details['eligible']} · độ phủ gốc tháng: {details['original_month_coverage']:.2%}"
        )
        heading.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(heading)
        self.canvas = FigureCanvasQTAgg(Figure(figsize=(10, 3), layout="constrained"))
        axes = self.canvas.figure.add_subplot(111)
        hours = np.arange(len(details["rows"])) * details["interval_minutes"] / 60
        for key, label, style in (
            ("original_kwh", "Gốc", "o--"),
            ("repaired_kwh", "Sau xử lý", "-"),
        ):
            vector = np.asarray([row[key] for row in details["rows"]], dtype=float)
            axes.plot(hours, vector, style, label=label)
        axes.set(xlabel="Giờ", ylabel="Điện năng chu kỳ (kWh)", xlim=(0, 24))
        axes.legend()
        axes.grid(alpha=0.2)
        layout.addWidget(self.canvas, 1)
        self.model = RecordsModel(self)
        self.model.set_records(details["rows"])
        table = QTableView()
        table.setModel(self.model)
        layout.addWidget(table, 1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
