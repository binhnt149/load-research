"""Desktop project workflow and responsive process supervision."""

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from load_research.application.jobs import ResearchJob
from load_research.application.models import StudyRequest, load_request
from load_research.error_messages import format_error
from load_research.ui.forms import ExportDialog, ResearchForm
from load_research.ui.inspection import DayInspectionDialog
from load_research.ui.results import ResultsView
from load_research.ui.theme import apply_theme
from load_research.workspace import Workspace, atomic_json


def scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    return area


class MainWindow(QMainWindow):
    result_ready = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Load Research · Nghiên cứu phụ tải")
        self.resize(1240, 860)
        apply_theme(self)
        self.workspace: Workspace | None = None
        self.job: ResearchJob | None = None
        self.current_result: dict | None = None
        self.last_error: str | None = None
        self.last_error_details: str | None = None
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        title = QLabel("Nghiên cứu phụ tải")
        title.setObjectName("heading")
        layout.addWidget(title)
        layout.addWidget(
            QLabel(
                "Biểu đồ ngành nghề · Dữ liệu có nguồn gốc · Phương pháp có thể kiểm tra lại"
            )
        )
        project_bar = QHBoxLayout()
        for text, callback in (
            ("Tạo dự án…", self.create_project_dialog),
            ("Mở dự án…", self.open_project_dialog),
            ("Nạp cấu hình…", self.load_request_dialog),
            ("Lưu cấu hình…", self.save_request_dialog),
            ("Sao lưu…", self.backup_dialog),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            project_bar.addWidget(button)
        self.project_label = QLabel("Chưa mở dự án")
        self.project_label.setObjectName("hint")
        project_bar.addWidget(self.project_label, 1)
        layout.addLayout(project_bar)
        self.form = ResearchForm()
        self.tabs = QTabWidget()
        self.tabs.addTab(scroll(self.form), "1 · Dữ liệu")
        self.tabs.addTab(scroll(self.form.config_form), "2 · Phương pháp")
        self.result_host = QWidget()
        self.result_layout = QVBoxLayout(self.result_host)
        self.results = ResultsView()
        self.results.rename_requested.connect(self.rename_cluster)
        self.results.export_requested.connect(self.export_dialog)
        self.results.inspect_requested.connect(
            lambda payload: self.start_auxiliary("inspect", payload)
        )
        self.result_layout.addWidget(self.results)
        self.tabs.addTab(self.result_host, "3 · Kết quả")
        history = QWidget()
        history_layout = QVBoxLayout(history)
        self.run_list = QListWidget()
        self.run_list.itemDoubleClicked.connect(lambda _item: self.load_selected_run())
        history_layout.addWidget(self.run_list)
        for text, callback in (
            ("Mở kết quả đã lưu", self.load_selected_run),
            ("Dùng lại cấu hình lần chạy", self.reuse_selected_request),
            ("So kết quả hiện tại với lần đang chọn", self.compare_selected_run),
            ("Làm mới lịch sử", self.refresh_history),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            history_layout.addWidget(button)
        self.tabs.addTab(history, "4 · Lịch sử")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.tabs.addTab(self.log, "Nhật ký tác vụ")
        layout.addWidget(self.tabs, 1)
        controls = QHBoxLayout()
        self.start_button = QPushButton("Chạy nghiên cứu")
        self.start_button.setObjectName("primary")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_research)
        self.cancel_button = QPushButton("Huỷ tác vụ")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(
            lambda: self.job.cancel() if self.job else None
        )
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status_label = QLabel("Sẵn sàng · mở hoặc tạo dự án để bắt đầu")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setObjectName("hint")
        self.status_label.setWordWrap(True)
        self.project_label.setTextFormat(Qt.TextFormat.PlainText)
        controls.addWidget(self.start_button)
        controls.addWidget(self.cancel_button)
        controls.addWidget(self.progress, 1)
        layout.addLayout(controls)
        layout.addWidget(self.status_label)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll_job)

    def open_project(self, path: Path) -> None:
        if self.job and self.job.is_running:
            raise ValueError(
                "finish or cancel the active job before switching projects"
            )
        self.workspace = Workspace.open(path)
        self.project_label.setText(f"Dự án: {self.workspace.root.name}")
        self.project_label.setToolTip(str(self.workspace.root))
        self.start_button.setEnabled(True)
        self.refresh_history()
        if self.workspace.list_runs():
            self.start_auxiliary("verify", {})

    def create_project_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục trống cho dự án mới"
        )
        if path:
            try:
                Workspace.create(Path(path))
                self.open_project(Path(path))
            except (OSError, ValueError) as error:
                self.show_error(str(error))

    def open_project_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Mở thư mục dự án")
        if path:
            try:
                self.open_project(Path(path))
            except (OSError, ValueError) as error:
                self.show_error(str(error))

    def set_request(self, request: StudyRequest) -> None:
        self.form.set_request(request)
        self.start_button.setEnabled(
            self.workspace is not None and not (self.job and self.job.is_running)
        )

    def build_request(self) -> StudyRequest:
        return self.form.build_request()

    def save_request_dialog(self) -> None:
        try:
            request = self.build_request()
            path, _filter = QFileDialog.getSaveFileName(
                self,
                "Lưu cấu hình nghiên cứu",
                "research-request.json",
                "JSON (*.json)",
            )
            if path:
                if Path(path).resolve() in request.all_paths():
                    raise ValueError("configuration cannot overwrite a source file")
                atomic_json(Path(path), request.to_dict(), replace=True)
        except (OSError, ValueError, TypeError) as error:
            self.show_error(str(error))

    def load_request_dialog(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, "Nạp cấu hình", "", "JSON (*.json)"
        )
        if path:
            try:
                self.set_request(load_request(Path(path)))
            except (OSError, ValueError, TypeError, KeyError) as error:
                self.show_error(str(error))

    def start_research(self) -> None:
        try:
            if self.workspace is None:
                raise ValueError("hãy mở hoặc tạo dự án")
            request = self.build_request()
            if self.job:
                self.job.close()
            self.last_error = None
            self.job = ResearchJob(self.workspace.root)
            self.job.start(request)
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.progress.setRange(0, 0)
            self.status_label.setText("Đang chuẩn bị và xác minh nguồn…")
            self.timer.start()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            self.show_error(str(error))

    def export_dialog(self, selected: bool) -> None:
        if not self.current_result or not self.workspace:
            self.show_error("Hãy mở một kết quả trước khi xuất.")
            return
        if self.job and self.job.is_running:
            self.show_error("Hãy đợi hoặc huỷ tác vụ đang chạy trước khi xuất.")
            return
        dialog = ExportDialog(self)
        if not dialog.exec():
            return
        path = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục cha để tạo bộ báo cáo"
        )
        if path:
            destination = Path(path) / f"report-{self.current_result['run_id'][:12]}"
            self.start_export(
                destination,
                {**self.results.export_options(selected=selected), **dialog.options()},
            )

    def start_export(self, destination: Path, options: dict) -> None:
        try:
            if not self.workspace or not self.current_result:
                raise ValueError("no completed result is loaded")
            if self.job and self.job.is_running:
                raise ValueError("another task is running")
            if self.job:
                self.job.close()
            self.last_error = None
            self.job = ResearchJob(self.workspace.root)
            self.job.start_export(self.current_result["run_id"], destination, options)
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.progress.setRange(0, 0)
            self.status_label.setText("Đang xuất báo cáo…")
            self.timer.start()
        except (OSError, ValueError, RuntimeError) as error:
            self.show_error(str(error))

    def start_auxiliary(self, action: str, payload: dict) -> None:
        try:
            if not self.workspace or self.job and self.job.is_running:
                raise ValueError("Hãy mở dự án và đợi/huỷ tác vụ đang chạy.")
            if self.job:
                self.job.close()
            self.last_error = None
            self.job = ResearchJob(self.workspace.root)
            self.job.start_auxiliary(action, payload)
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.progress.setRange(0, 0)
            self.status_label.setText(
                {
                    "verify": "Đang xác minh checksum nguồn…",
                    "inspect": "Đang truy vết dữ liệu ngày…",
                    "backup": "Đang tạo bản sao lưu…",
                }[action]
            )
            self.timer.start()
        except (OSError, ValueError, RuntimeError) as error:
            self.show_error(str(error))

    def backup_dialog(self) -> None:
        if not self.workspace:
            self.show_error("Hãy mở dự án trước khi sao lưu.")
            return
        answer = QMessageBox.question(
            self,
            "Bản sao lưu dự án",
            "Lưu kèm các tệp nguồn bên ngoài để có thể tái chạy trên máy khác?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return
        parent = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục cha bên ngoài dự án"
        )
        if parent:
            destination = (
                Path(parent)
                / f"backup-{self.workspace.project_id[:8]}-{datetime.now():%Y%m%d-%H%M%S}"
            )
            self.start_auxiliary(
                "backup",
                {
                    "destination": str(destination),
                    "include_sources": answer == QMessageBox.StandardButton.Yes,
                },
            )

    def poll_job(self) -> None:
        if self.job is None:
            return
        events = self.job.poll()
        finished = not self.job.is_running
        if finished:
            self.job.join(0)
            events.extend(self.job.poll())
        for event in events:
            stage = event["stage"]
            self.log.appendPlainText(json.dumps(event, ensure_ascii=False))
            if "total" in event:
                self.progress.setRange(0, event["total"])
                self.progress.setValue(event["completed"])
            self.status_label.setText(
                event.get("message", f"{stage} · {event.get('period', '')}")
            )
            if stage == "finished":
                self.load_run(event["run_id"])
                self.status_label.setText(
                    f"Đã hoàn tất · {event['status']} · xem chất lượng và trạng thái từng ngành-tháng"
                )
            elif stage == "error":
                self.show_error(
                    event["message"],
                    context=event.get("source_context"),
                    error_type=event.get("error_type"),
                )
            elif stage == "exported":
                self.status_label.setText(f"Đã xuất báo cáo: {event['destination']}")
            elif stage == "cancelled":
                self.status_label.setText(
                    "Đã huỷ · kết quả hoàn thành trước đó được giữ"
                )
            elif stage == "sources_verified":
                changed = event["changed_count"]
                self.status_label.setText(
                    f"Đã xác minh {event['source_count']} nguồn · {changed} nguồn thiếu/thay đổi. "
                    + (
                        "Vẫn xem được kết quả đã lưu; cần khôi phục nguồn trước khi tái chạy."
                        if changed
                        else "Có thể tái chạy từ các nguồn đã xác minh."
                    )
                )
            elif stage == "backed_up":
                self.status_label.setText(f"Đã sao lưu: {event['destination']}")
            elif stage == "inspected":
                self.inspection_dialog = DayInspectionDialog(event["details"], self)
                self.inspection_dialog.show()
                self.status_label.setText(
                    "Đã truy vết dữ liệu ngày từ cấu hình và dữ liệu chuẩn đã lưu."
                )
        if finished:
            self.timer.stop()
            self.start_button.setEnabled(self.workspace is not None)
            self.cancel_button.setEnabled(False)
            self.progress.setRange(0, 100)
            if self.job.process and self.job.process.exitcode not in (None, 0):
                self.show_error(
                    f"Worker đã dừng bất thường (mã {self.job.process.exitcode}); kiểm tra lịch sử trước khi chạy lại."
                )
            self.job.close()
            self.refresh_history()

    def refresh_history(self) -> None:
        self.run_list.clear()
        if self.workspace:
            for run in self.workspace.list_runs():
                self.run_list.addItem(
                    f"{run['id']} · {run['status']} · {','.join(run['config']['periods'])}"
                )

    def load_run(self, run_id: str) -> None:
        if self.workspace is None:
            return
        result = self.workspace.load_artifact(run_id, "result.json")
        if not isinstance(result, dict):
            raise ValueError("invalid result schema")
        self.current_result = result
        self.results.set_result(result, self.workspace.list_cluster_labels(run_id))
        self.result_ready.emit(result)
        self.tabs.setCurrentIndex(2)

    def load_selected_run(self) -> None:
        item = self.run_list.currentItem()
        if item:
            try:
                self.load_run(item.text().split(" · ")[0])
            except (ValueError, OSError) as error:
                self.show_error(str(error))

    def reuse_selected_request(self) -> None:
        item = self.run_list.currentItem()
        if item and self.workspace:
            self.set_request(
                self.workspace.request_for_run(item.text().split(" · ")[0])
            )
            self.tabs.setCurrentIndex(0)

    def show_error(
        self,
        message: str,
        *,
        context: dict | None = None,
        error_type: str | None = None,
    ) -> None:
        self.last_error_details = message
        self.last_error = format_error(message, context, error_type=error_type)
        self.status_label.setText(f"Cần xử lý: {self.last_error}")
        self.log.appendPlainText(self.last_error)

    def compare_selected_run(self) -> None:
        item = self.run_list.currentItem()
        if item and self.workspace and self.current_result:
            try:
                result = self.workspace.load_artifact(
                    item.text().split(" · ")[0], "result.json"
                )
                self.results.set_comparison(result)
                self.tabs.setCurrentIndex(2)
            except (OSError, ValueError) as error:
                self.show_error(str(error))

    def rename_cluster(self, payload: dict) -> None:
        if self.workspace and self.current_result:
            try:
                run_id = self.current_result["run_id"]
                self.workspace.add_cluster_label(run_id, **payload)
                self.results.set_result(
                    self.current_result, self.workspace.list_cluster_labels(run_id)
                )
            except ValueError as error:
                self.show_error(str(error))

    def closeEvent(self, event) -> None:
        self.timer.stop()
        if self.job:
            self.job.close()
        event.accept()
