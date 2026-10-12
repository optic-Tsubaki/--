"""Non-blocking local chat panel for the user-configured AI provider."""

from __future__ import annotations

from pathlib import Path
import sys

import html

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

from ai.provider_manager import ProviderManager
from ai.providers.base import ChatMessage
from core.chat_history import ChatHistory
from core.app_paths import AppPaths
from config.settings_service import SettingsService
from security.credential_store import CredentialStore


class ChatWorker(QThread):
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, manager: ProviderManager, messages: list[ChatMessage]) -> None:
        super().__init__()
        self._manager = manager
        self._messages = messages

    def run(self) -> None:
        try:
            reply = self._manager.create_provider().chat(self._messages)
        except RuntimeError as error:
            self.failed.emit(str(error))
        except Exception as error:  # Last-resort UI boundary for unexpected provider failures.
            self.failed.emit(f"发送失败：{error}")
        else:
            self.completed.emit(reply or "（AI 未返回文本）")


class ChatPanel(QWidget):
    """本地保留聊天记录的非阻塞 AI 对话界面。"""

    def __init__(self, settings_service: SettingsService, credentials: CredentialStore) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._credentials = credentials
        if getattr(sys, "frozen", False):
            runtime_root = Path(sys.executable).resolve().parent
        else:
            runtime_root = Path(__file__).resolve().parents[1]
        paths = AppPaths.for_project(runtime_root)
        paths.ensure_exists()
        self._chat_history = ChatHistory(paths.database_file)
        self._stored_history = self._chat_history.recent()
        self._messages: list[ChatMessage] = [
            ChatMessage("system", "你是 StudyPet，一位温柔、简洁的学习与工作陪伴助手。")
        ]
        self._worker: ChatWorker | None = None
        self._build_ui()
        self._restore_local_history()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        title = QLabel("和 StudyPet 聊聊")
        title.setStyleSheet("font-size: 21px; font-weight: 700; color: #193C37;")
        layout.addWidget(title)
        note = QLabel("聊天会使用“设置”中由你自行配置的 AI 服务。")
        note.setStyleSheet("color: #6A7E78; padding-bottom: 4px;")
        layout.addWidget(note)
        self._history = QTextEdit()
        self._history.setReadOnly(True)
        self._history.setPlaceholderText("配置 AI 后，可以在这里开始对话。")
        layout.addWidget(self._history, 1)
        self._input = QPlainTextEdit()
        self._input.setPlaceholderText("输入消息…")
        self._input.setFixedHeight(76)
        layout.addWidget(self._input)
        actions = QHBoxLayout()
        self._send = QPushButton("发送")
        self._send.clicked.connect(self._send_message)
        actions.addStretch()
        self._clear_history = QPushButton("清空本地记录")
        self._clear_history.clicked.connect(self._clear_local_history)
        actions.addWidget(self._clear_history)
        actions.addWidget(self._send)
        layout.addLayout(actions)

    def _send_message(self) -> None:
        text = self._input.toPlainText().strip()
        if not text or self._worker is not None:
            return
        self._messages.append(ChatMessage("user", text))
        self._chat_history.add("user", text)
        self._append("你", text)
        self._input.clear()
        self._send.setEnabled(False)
        settings = self._settings_service.load()
        request_messages = list(self._messages)
        if settings.ai.use_chat_history:
            request_messages = [self._messages[0]]
            request_messages.extend(
                ChatMessage(item.role, item.content) for item in self._chat_history.recent()
            )
        self._worker = ChatWorker(ProviderManager(settings.ai, self._credentials), request_messages)
        self._worker.completed.connect(self._chat_completed)
        self._worker.failed.connect(self._chat_failed)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _chat_completed(self, reply: str) -> None:
        self._messages.append(ChatMessage("assistant", reply))
        self._chat_history.add("assistant", reply)
        self._append("StudyPet", reply)

    def _chat_failed(self, error: str) -> None:
        failed_message = self._messages.pop().content  # Let the user retry the unchanged message.
        self._chat_history.remove_latest("user", failed_message)
        self._append("提示", error)

    def _worker_finished(self) -> None:
        self._send.setEnabled(True)
        self._worker = None

    def _clear_local_history(self) -> None:
        if self._worker is not None:
            return
        answer = QMessageBox.question(
            self,
            "清空本地聊天记录",
            "确定清空这台电脑上的全部聊天记录吗？此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._chat_history.clear()
        self._stored_history = []
        self._messages = self._messages[:1]
        self._history.clear()

    def _restore_local_history(self) -> None:
        for item in self._stored_history:
            speaker = "你" if item.role == "user" else "StudyPet"
            self._append(speaker, item.content)

    def _append(self, speaker: str, content: str) -> None:
        self._history.append(f"<b>{html.escape(speaker)}</b><br>{html.escape(content).replace(chr(10), '<br>')}<br>")
