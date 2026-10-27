"""Reuse the bounded source preview; the worker validates the complete catalog."""

from PySide6.QtWidgets import QDialogButtonBox, QLabel

from load_research.components import parse_components
from load_research.error_messages import format_error
from load_research.ui.source_preview import SourcePreviewDialog


class ComponentImportDialog(SourcePreviewDialog):
    def __init__(self, path, parent=None):
        super().__init__(path, parent=parent)
        self.setWindowTitle("Nhập danh mục thành phần phụ tải")
        for label in self.findChildren(QLabel):
            if label.text().startswith("Chỉ xem trước"):
                label.setText(
                    "Kiểm tra 4 cột mã/tên ngành nghề và mã/tên thành phần. Sheet/dấu phân cách đã chọn được dùng khi nhập toàn bộ tệp trong tiến trình nền."
                )
        buttons = self.findChild(QDialogButtonBox)
        assert buttons is not None
        button = buttons.addButton(
            "Nhập danh mục", QDialogButtonBox.ButtonRole.AcceptRole
        )
        button.clicked.connect(self.validate_preview)

    def validate_preview(self):
        try:
            parse_components(self.model.records)
        except (ValueError, TypeError) as error:
            self.status.setText(format_error(error))
        else:
            self.accept()

    def options(self):
        return {
            "path": str(self.path),
            "sheet": self.sheet.currentText() or None,
            "delimiter": self.delimiter.currentData(),
        }
