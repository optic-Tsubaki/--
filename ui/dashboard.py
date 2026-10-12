"""The initial local task and focus dashboard."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.task_manager import TaskManager
from core.timer import FocusTimer
from config.settings_service import SettingsService
from security.credential_store import CredentialStore
from ui.settings_panel import SettingsPanel


class Dashboard(QDialog):
    """Small, usable V0.2 panel for tasks and local focus sessions."""

    def __init__(
        self,
        tasks: TaskManager,
        focus_timer: FocusTimer,
        settings_service: SettingsService,
        credentials: CredentialStore,
    ) -> None:
        super().__init__()
        self._tasks = tasks
        self._focus_timer = focus_timer
        self.setWindowTitle("StudyPet 控制面板")
        self.setMinimumSize(560, 430)

        self._tabs = QTabWidget()
        self._task_table = QTableWidget(0, 3)
        self._timer_label = QLabel("00:00:00")
        self._today_label = QLabel()
        self._timer_task = QComboBox()
        self._start_stop_button = QPushButton()
        self._build_tasks_tab()
        self._build_timer_tab()
        self._build_stats_tab()
        self._build_settings_tab(settings_service, credentials)

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

        self._ticker = QTimer(self)
        self._ticker.setInterval(500)
        self._ticker.timeout.connect(self._refresh_timer_display)
        self._ticker.start()
        self._refresh_all()

    def open_section(self, section: str = "tasks") -> None:
        index = {"tasks": 0, "timer": 1, "stats": 2, "settings": 3}.get(section, 0)
        self._refresh_all()
        self._tabs.setCurrentIndex(index)
        self.show()
        self.raise_()
        self.activateWindow()

    def _build_tasks_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QHBoxLayout()
        self._task_title = QLineEdit()
        self._task_title.setPlaceholderText("例如：完成数学复习")
        self._task_category = QComboBox()
        self._task_category.addItems(["学习", "科研", "工作", "生活"])
        add_button = QPushButton("添加任务")
        add_button.clicked.connect(self._add_task)
        form.addWidget(self._task_title, 1)
        form.addWidget(self._task_category)
        form.addWidget(add_button)
        layout.addLayout(form)

        self._task_table.setHorizontalHeaderLabels(["任务", "分类", "创建时间"])
        self._task_table.horizontalHeader().setStretchLastSection(True)
        self._task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._task_table.itemChanged.connect(self._task_changed)
        layout.addWidget(self._task_table)
        self._tabs.addTab(page, "今日任务")

    def _build_timer_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer_label.setStyleSheet("font-size: 42px; font-weight: 600; color: #365f52; padding: 24px;")
        layout.addWidget(self._timer_label)

        form = QFormLayout()
        form.addRow("关联任务：", self._timer_task)
        layout.addLayout(form)
        self._start_stop_button.clicked.connect(self._toggle_timer)
        layout.addWidget(self._start_stop_button)
        layout.addWidget(QLabel("结束计时后，时长会自动保存到本机。"))
        self._tabs.addTab(page, "专注计时")

    def _build_stats_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = QLabel("今日专注统计")
        title.setStyleSheet("font-size: 22px; font-weight: 600; padding-top: 24px;")
        self._today_label.setStyleSheet("font-size: 34px; color: #365f52; padding: 12px 0;")
        layout.addWidget(title)
        layout.addWidget(self._today_label)
        layout.addWidget(QLabel("更多日、周、月统计将在后续版本提供。"))
        self._tabs.addTab(page, "学习统计")

    def _build_settings_tab(
        self, settings_service: SettingsService, credentials: CredentialStore
    ) -> None:
        self._tabs.addTab(SettingsPanel(settings_service, credentials), "设置")

    def _add_task(self) -> None:
        try:
            self._tasks.add_task(self._task_title.text(), self._task_category.currentText())
        except ValueError as error:
            QMessageBox.information(self, "无法添加任务", str(error))
            return
        self._task_title.clear()
        self._refresh_all()

    def _task_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if task_id is None:
            return
        self._tasks.set_completed(int(task_id), item.checkState() == Qt.CheckState.Checked)
        self._refresh_timer_tasks()

    def _toggle_timer(self) -> None:
        if self._focus_timer.is_running:
            self._focus_timer.stop()
        else:
            task_id = self._timer_task.currentData()
            self._focus_timer.start(int(task_id) if task_id is not None else None)
        self._refresh_timer_display()

    def _refresh_all(self) -> None:
        self._refresh_task_table()
        self._refresh_timer_tasks()
        self._refresh_timer_display()

    def _refresh_task_table(self) -> None:
        self._task_table.blockSignals(True)
        tasks = self._tasks.list_tasks()
        self._task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            title = QTableWidgetItem(task.title)
            title.setData(Qt.ItemDataRole.UserRole, task.id)
            title.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            title.setCheckState(Qt.CheckState.Checked if task.completed else Qt.CheckState.Unchecked)
            self._task_table.setItem(row, 0, title)
            self._task_table.setItem(row, 1, QTableWidgetItem(task.category))
            self._task_table.setItem(row, 2, QTableWidgetItem(task.created_at.replace("T", " ")))
        self._task_table.blockSignals(False)

    def _refresh_timer_tasks(self) -> None:
        selected_task = self._timer_task.currentData()
        self._timer_task.blockSignals(True)
        self._timer_task.clear()
        self._timer_task.addItem("不关联任务", None)
        for task in self._tasks.list_tasks():
            if not task.completed:
                self._timer_task.addItem(f"{task.category} · {task.title}", task.id)
        index = self._timer_task.findData(selected_task)
        if index >= 0:
            self._timer_task.setCurrentIndex(index)
        self._timer_task.blockSignals(False)

    def _refresh_timer_display(self) -> None:
        seconds = self._focus_timer.elapsed_seconds()
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self._timer_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
        self._start_stop_button.setText("结束计时" if self._focus_timer.is_running else "开始计时")
        total = self._focus_timer.total_today_seconds()
        total_hours, total_remainder = divmod(total, 3600)
        total_minutes = total_remainder // 60
        self._today_label.setText(f"{total_hours} 小时 {total_minutes:02} 分钟")
