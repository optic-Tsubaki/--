"""The initial local task and focus dashboard."""

from __future__ import annotations

import csv
from typing import Callable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
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
from ui.chat_panel import ChatPanel
from ui.settings_panel import SettingsPanel


class Dashboard(QDialog):
    """Small, usable V0.2 panel for tasks and local focus sessions."""

    def __init__(
        self,
        tasks: TaskManager,
        focus_timer: FocusTimer,
        settings_service: SettingsService,
        credentials: CredentialStore,
        on_focus_started: Callable[[str], None] | None = None,
        on_focus_finished: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__()
        self._tasks = tasks
        self._focus_timer = focus_timer
        self._on_focus_started = on_focus_started
        self._on_focus_finished = on_focus_finished
        self.setWindowTitle("StudyPet 控制面板")
        self.setMinimumSize(680, 520)
        self._apply_style()

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._task_table = QTableWidget(0, 3)
        self._timer_label = QLabel("00:00:00")
        self._today_label = QLabel()
        self._session_table = QTableWidget(0, 3)
        self._timer_task = QComboBox()
        self._start_stop_button = QPushButton()
        self._build_tasks_tab()
        self._build_timer_tab()
        self._build_stats_tab()
        self._build_chat_tab(settings_service, credentials)
        self._build_settings_tab(settings_service, credentials)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)
        layout.addWidget(self._build_header())
        layout.addWidget(self._tabs)

        self._ticker = QTimer(self)
        self._ticker.setInterval(500)
        self._ticker.timeout.connect(self._refresh_timer_display)
        self._ticker.start()
        self._refresh_all()

    def _apply_style(self) -> None:
        """A compact dark-mint visual system shared by every dashboard tab."""
        self.setStyleSheet(
            """
            QDialog { background: #F3F7F5; color: #1D2A29; font-family: 'Microsoft YaHei UI'; }
            QWidget#dashboardHeader { background: #193C37; border-radius: 18px; }
            QLabel#appTitle { color: #FFFFFF; font-size: 25px; font-weight: 700; }
            QLabel#appSubtitle { color: #BBD2CD; font-size: 12px; }
            QLabel#statusPill { background: #C9F36A; color: #234039; border-radius: 11px; padding: 5px 11px; font-weight: 600; }
            QTabWidget::pane { background: #FFFFFF; border: 1px solid #DCE9E5; border-radius: 16px; top: -1px; }
            QTabBar::tab { background: transparent; color: #637571; padding: 10px 14px; margin-right: 4px; font-weight: 600; }
            QTabBar::tab:selected { color: #193C37; border-bottom: 3px solid #5FC8A6; }
            QTabBar::tab:hover { color: #193C37; }
            QLineEdit, QPlainTextEdit, QComboBox { background: #F8FBFA; border: 1px solid #D7E6E1; border-radius: 10px; padding: 8px 10px; selection-background-color: #A7E5D0; }
            QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border: 2px solid #5FC8A6; }
            QPushButton { background: #1F786B; color: white; border: none; border-radius: 10px; padding: 9px 15px; font-weight: 600; }
            QPushButton:hover { background: #276D63; }
            QPushButton:pressed { background: #15564D; }
            QPushButton:disabled { background: #B6C9C4; }
            QTableWidget { background: #FFFFFF; border: 1px solid #E0ECE8; border-radius: 10px; gridline-color: transparent; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #EDF3F1; }
            QTableWidget::item:selected { background: #E5F6EF; color: #193C37; }
            QHeaderView::section { background: #EFF6F3; color: #56706A; border: none; padding: 9px; font-weight: 600; }
            QTextEdit { background: #F8FBFA; border: 1px solid #D7E6E1; border-radius: 12px; padding: 8px; }
            """
        )

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("dashboardHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        text_layout = QVBoxLayout()
        title = QLabel("StudyPet")
        title.setObjectName("appTitle")
        subtitle = QLabel("你的本地学习伙伴 · 任务、专注与陪伴都在这里")
        subtitle.setObjectName("appSubtitle")
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        status = QLabel("● 本地优先")
        status.setObjectName("statusPill")
        header_layout.addLayout(text_layout)
        header_layout.addStretch()
        header_layout.addWidget(status, alignment=Qt.AlignmentFlag.AlignTop)
        return header

    def open_section(self, section: str = "tasks") -> None:
        index = {"tasks": 0, "timer": 1, "stats": 2, "chat": 3, "settings": 4}.get(section, 0)
        self._refresh_all()
        self._tabs.setCurrentIndex(index)
        self.show()
        self.raise_()
        self.activateWindow()

    def _build_tasks_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        hint = QLabel("把今天最重要的事写下来，完成后勾选即可。")
        hint.setStyleSheet("color: #6A7E78; padding-bottom: 4px;")
        layout.addWidget(hint)
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
        self._task_table.setAlternatingRowColors(False)
        self._task_table.verticalHeader().setVisible(False)
        self._task_table.horizontalHeader().setStretchLastSection(True)
        self._task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._task_table.itemChanged.connect(self._task_changed)
        layout.addWidget(self._task_table)
        self._tabs.addTab(page, "今日任务")

    def _build_timer_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 32, 42, 32)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        eyebrow = QLabel("FOCUS SESSION")
        eyebrow.setStyleSheet("color: #5A8D7F; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eyebrow)
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer_label.setStyleSheet("font-size: 52px; font-weight: 700; color: #193C37; padding: 18px;")
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
        layout.setContentsMargins(42, 32, 42, 32)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = QLabel("今日专注统计")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #193C37; padding-top: 12px;")
        self._today_label.setStyleSheet("font-size: 40px; font-weight: 700; color: #1F786B; padding: 12px 0;")
        layout.addWidget(title)
        layout.addWidget(self._today_label)
        recent_title = QLabel("最近专注记录")
        recent_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #193C37; padding-top: 14px;")
        layout.addWidget(recent_title)
        self._session_table.setHorizontalHeaderLabels(["开始时间", "任务", "时长"])
        self._session_table.horizontalHeader().setStretchLastSection(True)
        self._session_table.verticalHeader().setVisible(False)
        self._session_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._session_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._session_table, 1)
        export_button = QPushButton("导出全部记录为 CSV")
        export_button.clicked.connect(self._export_records)
        layout.addWidget(export_button)
        self._tabs.addTab(page, "学习统计")

    def _build_settings_tab(
        self, settings_service: SettingsService, credentials: CredentialStore
    ) -> None:
        self._tabs.addTab(SettingsPanel(settings_service, credentials), "设置")

    def _build_chat_tab(self, settings_service: SettingsService, credentials: CredentialStore) -> None:
        self._tabs.addTab(ChatPanel(settings_service, credentials), "AI 聊天")

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
            duration = self._focus_timer.stop()
            if self._on_focus_finished is not None:
                self._on_focus_finished(duration)
        else:
            task_id = self._timer_task.currentData()
            self._focus_timer.start(int(task_id) if task_id is not None else None)
            if self._on_focus_started is not None:
                label = self._timer_task.currentText()
                self._on_focus_started(label if task_id is not None else "自由专注")
        self._refresh_timer_display()
        self._refresh_session_table()

    def _refresh_all(self) -> None:
        self._refresh_task_table()
        self._refresh_timer_tasks()
        self._refresh_timer_display()
        self._refresh_session_table()

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

    def _refresh_session_table(self) -> None:
        sessions = self._focus_timer.list_recent_sessions()
        self._session_table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            self._session_table.setItem(row, 0, QTableWidgetItem(session.started_at.replace("T", " ")))
            self._session_table.setItem(row, 1, QTableWidgetItem(session.task_title or "自由专注"))
            self._session_table.setItem(row, 2, QTableWidgetItem(self._format_duration(session.duration_seconds)))

    def _export_records(self) -> None:
        default_name = "StudyPet-专注记录.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "导出专注记录", default_name, "CSV 文件 (*.csv)")
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as output:
                writer = csv.writer(output)
                writer.writerow(["开始时间", "任务", "专注时长（秒）", "专注时长"])
                for session in self._focus_timer.list_recent_sessions(limit=10000):
                    writer.writerow(
                        [
                            session.started_at.replace("T", " "),
                            session.task_title or "自由专注",
                            session.duration_seconds,
                            self._format_duration(session.duration_seconds),
                        ]
                    )
        except OSError as error:
            QMessageBox.warning(self, "导出失败", str(error))
            return
        QMessageBox.information(self, "导出完成", f"记录已导出到：\n{file_path}")

    @staticmethod
    def _format_duration(total_seconds: int) -> str:
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours} 小时 {minutes:02} 分钟"
        if minutes:
            return f"{minutes} 分钟 {seconds:02} 秒"
        return f"{seconds} 秒"
