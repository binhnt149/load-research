"""Inspect input examples and save a fresh template without overwriting sources."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
)

from load_research.input_templates import NOTICE, TEMPLATES, write_template
from load_research.ui.models import RecordsModel


class TemplateDialog(QDialog):
    def __init__(self, *, category: str, parent=None) -> None:
        super().__init__(parent)
        self.category = category
        self.setWindowTitle("Tệp mẫu dữ liệu đầu vào")
        self.resize(1020, 620)
        layout = QVBoxLayout(self)
        title = QLabel("Chuẩn bị tệp đúng định dạng")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self.selector = QComboBox()
        self.selector.setAccessibleName("Loại tệp mẫu")
        for key, template in TEMPLATES.items():
            if template.category == category:
                self.selector.addItem(template.title, key)
        layout.addWidget(self.selector)
        self.guidance = QLabel()
        self.guidance.setTextFormat(Qt.TextFormat.PlainText)
        self.guidance.setWordWrap(True)
        layout.addWidget(self.guidance)
        tabs = QTabWidget()
        self.example_model, self.field_model = RecordsModel(self), RecordsModel(self)
        for name, model in (
            ("Dữ liệu minh hoạ", self.example_model),
            ("Hướng dẫn từng cột", self.field_model),
        ):
            table = QTableView()
            table.setModel(model)
            table.setAlternatingRowColors(True)
            table.horizontalHeader().setDefaultSectionSize(
                165 if model is self.example_model else 460
            )
            tabs.addTab(table, name)
        layout.addWidget(tabs, 1)
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.save_button = QPushButton("Lưu tệp mẫu…")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self.save_template)
        buttons.addWidget(self.save_button)
        buttons.addStretch()
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.selector.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_args) -> None:
        template = TEMPLATES[self.selector.currentData()]
        self.guidance.setText(f"{NOTICE}\n{template.guidance}")
        self.example_model.set_records([dict(row) for row in template.examples])
        self.field_model.set_records(
            [
                {"Trường": name, "Hướng dẫn": template.column_help(name)}
                for name in template.columns
            ]
        )
        self.status.clear()

    def save_template(self) -> None:
        key = self.selector.currentData()
        filename, selected_filter = QFileDialog.getSaveFileName(
            self, "Lưu tệp mẫu mới", f"{key}.xlsx", "Excel (*.xlsx);;CSV UTF-8 (*.csv)"
        )
        if not filename:
            return
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix(
                ".csv" if selected_filter.startswith("CSV") else ".xlsx"
            )
        try:
            write_template(key, path)
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
        else:
            self.status.setText(
                f"Đã lưu: {path}\nXLSX có sheet Hướng dẫn; giữ mã dạng chuỗi khi sửa dữ liệu."
            )
