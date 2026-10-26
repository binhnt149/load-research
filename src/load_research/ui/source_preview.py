"""Bounded, read-only source preview with recoverable file options."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from load_research.importers.tables import excel_sheets, read_preview
from load_research.ui.models import RecordsModel


class SourcePreviewDialog(QDialog):
    def __init__(
        self,
        path: str,
        *,
        limit: int = 50,
        sheet: str | None = None,
        delimiter: str = ",",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.path, self.limit = Path(path), limit
        self.setWindowTitle("Xem trước dữ liệu nguồn")
        self.resize(1040, 620)
        self.setMinimumSize(620, 400)
        layout = QVBoxLayout(self)
        title = QLabel(self.path.name)
        title.setObjectName("sectionTitle")
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setWordWrap(True)
        layout.addWidget(title)
        location = QLabel(str(self.path))
        location.setTextFormat(Qt.TextFormat.PlainText)
        location.setWordWrap(True)
        location.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(location)
        controls = QHBoxLayout()
        self.sheet, self.delimiter = QComboBox(), QComboBox()
        self.sheet.setAccessibleName("Sheet Excel xem trước")
        self.delimiter.setAccessibleName("Dấu phân cách CSV xem trước")
        if self.path.suffix.lower() == ".xlsx":
            try:
                self.sheet.addItems(excel_sheets(self.path))
            except Exception:
                # Reload below presents the file-reader error in the dialog.
                self.sheet.addItem(sheet or "")
        if sheet:
            if self.sheet.findText(sheet) < 0:
                self.sheet.addItem(sheet)
            self.sheet.setCurrentText(sheet)
        for label, value in (
            ("Dấu phẩy (,)", ","),
            ("Chấm phẩy (;)", ";"),
            ("Tab", "\t"),
            ("Gạch đứng (|)", "|"),
        ):
            self.delimiter.addItem(label, value)
        if self.delimiter.findData(delimiter) < 0:
            self.delimiter.addItem(repr(delimiter), delimiter)
        self.delimiter.setCurrentIndex(self.delimiter.findData(delimiter))
        self.sheet.setEnabled(self.path.suffix.lower() == ".xlsx")
        self.delimiter.setEnabled(self.path.suffix.lower() == ".csv")
        controls.addWidget(QLabel("Sheet Excel"))
        controls.addWidget(self.sheet, 1)
        controls.addWidget(QLabel("Dấu phân cách CSV"))
        controls.addWidget(self.delimiter)
        self.reload_button = QPushButton("Đọc lại")
        controls.addWidget(self.reload_button)
        layout.addLayout(controls)
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.model = RecordsModel(self, localized=False)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        note = QLabel(
            "Chỉ xem trước, không sửa tệp gốc. Sheet/dấu phân cách tại đây chỉ dùng để xem; "
            "hãy khai báo tương ứng trong thiết lập nguồn trước khi chạy."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Đóng")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.reload_button.clicked.connect(self.reload)
        self.sheet.currentIndexChanged.connect(self.reload)
        self.delimiter.currentIndexChanged.connect(self.reload)
        self.reload()

    def reload(self, *_args) -> None:
        self.model.set_records([])
        try:
            preview = read_preview(
                self.path,
                limit=self.limit,
                sheet=self.sheet.currentText() or None,
                delimiter=self.delimiter.currentData(),
            )
        except Exception as error:
            # File parsers expose several exception families; keep this UI recoverable.
            self.status.setProperty("tone", "danger")
            self.status.setText(f"Không đọc được dữ liệu: {error}")
        else:
            self.model.set_records(preview.rows, list(preview.columns))
            self.table.resizeColumnsToContents()
            for index in range(len(preview.columns)):
                self.table.setColumnWidth(
                    index, min(320, max(110, self.table.columnWidth(index)))
                )
            self.status.setProperty("tone", "neutral")
            summary = f"{len(preview.rows)} dòng hiển thị · {len(preview.columns)} cột"
            if not preview.rows:
                summary += " · chỉ có tiêu đề, chưa có dòng dữ liệu"
            elif preview.has_more:
                summary += f" · giới hạn {self.limit} dòng đầu, còn dữ liệu phía sau"
            if len(preview.columns) == 1 and self.path.suffix.lower() == ".csv":
                summary += ". Nếu dữ liệu dồn vào một cột, hãy đổi dấu phân cách."
            self.status.setText(summary)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
