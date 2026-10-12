"""Non-blocking local chat panel for the user-configured AI provider."""

from __future__ import annotations

import html

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

from ai.provider_manager import ProviderManager
from ai.providers.base import ChatMessage
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
    """A short-lived conversation UI; persistence and memory come in a later phase."""

    def __init__(self, settings_service: SettingsService, credentials: CredentialStore) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._credentials = credentials
        self._messages: list[ChatMessage] = [
            ChatMessage("system", "你是 StudyPet，一位温柔、简洁的学习与工作陪伴助手。")
        ]
        self._worker: ChatWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        note = QLabel("聊天会使用“设置”中由你自行配置的 AI 服务。")
        note.setStyleSheet("color: #52616b;")
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
        actions.addWidget(self._send)
        layout.addLayout(actions)

    def _send_message(self) -> None:
        text = self._input.toPlainText().strip()
        if not text or self._worker is not None:
            return
        self._messages.append(ChatMessage("user", text))
        self._append("你", text)
        self._input.clear()
        self._send.setEnabled(False)
        settings = self._settings_service.load()
        self._worker = ChatWorker(ProviderManager(settings.ai, self._credentials), list(self._messages))
        self._worker.completed.connect(self._chat_completed)
        self._worker.failed.connect(self._chat_failed)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _chat_completed(self, reply: str) -> None:
        self._messages.append(ChatMessage("assistant", reply))
        self._append("StudyPet", reply)

    def _chat_failed(self, error: str) -> None:
        self._messages.pop()  # Let the user retry the unchanged message.
        self._append("提示", error)

    def _worker_finished(self) -> None:
        self._send.setEnabled(True)
        self._worker = None

    def _append(self, speaker: str, content: str) -> None:
        self._history.append(f"<b>{html.escape(speaker)}</b><br>{html.escape(content).replace(chr(10), '<br>')}<br>")
