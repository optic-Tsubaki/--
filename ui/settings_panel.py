"""A local, credential-safe AI configuration panel."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.ai_config import AIConfig, ProviderKind
from config.settings_service import AppSettings, SettingsService
from security.credential_store import CredentialStore
from ai.providers.base import ChatMessage
from ai.providers.ollama import OllamaProvider
from ai.providers.openai_compatible import OpenAICompatibleProvider


class ConnectionTestWorker(QThread):
    """Performs an explicitly user-requested provider check off the UI thread."""

    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, config: AIConfig, temporary_api_key: str, credentials: CredentialStore) -> None:
        super().__init__()
        self._config = config
        self._temporary_api_key = temporary_api_key
        self._credentials = credentials

    def run(self) -> None:
        try:
            if self._config.provider is ProviderKind.OPENAI_COMPATIBLE:
                api_key = self._temporary_api_key or self._credentials.get_api_key(self._config.provider)
                if not api_key:
                    raise RuntimeError("请输入 API Key，或先保存已有的 API Key。")
                provider = OpenAICompatibleProvider(
                    self._config.base_url, self._config.model, api_key
                )
            elif self._config.provider is ProviderKind.OLLAMA:
                provider = OllamaProvider(self._config.base_url, self._config.model)
            else:
                raise RuntimeError("请选择 AI 服务商。")
            reply = provider.chat(
                [ChatMessage("user", "Reply with only: connection-ok")]
            )
        except RuntimeError as error:
            self.failed.emit(str(error))
        except Exception as error:
            self.failed.emit(f"测试失败：{error}")
        else:
            self.succeeded.emit(reply)


class SettingsPanel(QWidget):
    """Stores safe AI metadata locally and keys in the OS credential manager."""

    _PROVIDERS = (
        ("不使用 AI（普通模式）", ProviderKind.NONE),
        ("OpenAI 兼容 API", ProviderKind.OPENAI_COMPATIBLE),
        ("Ollama 本地模型", ProviderKind.OLLAMA),
    )

    def __init__(self, settings_service: SettingsService, credentials: CredentialStore) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._credentials = credentials
        self._test_worker: ConnectionTestWorker | None = None
        self._build_ui()
        self.load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("AI 模型设置")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #193C37;")
        layout.addWidget(title)
        note = QLabel("API Key 仅保存在 Windows 凭据管理器，不会写入设置文件或数据库。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #6A7E78; padding: 4px 0 12px;")
        layout.addWidget(note)

        form = QFormLayout()
        self._provider = QComboBox()
        for label, provider in self._PROVIDERS:
            self._provider.addItem(label, provider)
        self._base_url = QLineEdit()
        self._base_url.setPlaceholderText("例如：https://api.openai.com/v1")
        self._model = QLineEdit()
        self._model.setPlaceholderText("例如：gpt-4.1-mini 或 deepseek-chat")
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("留空代表不修改已保存的 Key")
        form.addRow("服务商：", self._provider)
        form.addRow("Base URL：", self._base_url)
        form.addRow("模型名称：", self._model)
        form.addRow("API Key：", self._api_key)
        layout.addLayout(form)
        self._use_chat_history = QCheckBox("允许将近期本地聊天记录发送给当前 AI，作为对话上下文")
        self._use_chat_history.setToolTip("默认关闭。启用后，近期聊天会随请求发送给你选择的 AI 服务商。")
        layout.addWidget(self._use_chat_history)

        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        actions = QHBoxLayout()
        self._test_button = QPushButton("测试当前输入")
        self._test_button.clicked.connect(self.test_connection)
        save_button = QPushButton("保存 AI 设置")
        save_button.clicked.connect(self.save_settings)
        actions.addWidget(self._test_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)
        layout.addStretch()
        self._provider.currentIndexChanged.connect(self._refresh_enabled_state)

    def load_settings(self) -> None:
        settings = self._settings_service.load()
        index = self._provider.findData(settings.ai.provider)
        self._provider.setCurrentIndex(max(index, 0))
        self._base_url.setText(settings.ai.base_url)
        self._model.setText(settings.ai.model)
        self._use_chat_history.setChecked(settings.ai.use_chat_history)
        self._api_key.clear()
        self._refresh_enabled_state()

    def save_settings(self) -> None:
        provider = self._provider.currentData()
        config = AIConfig(
            provider=provider,
            base_url=self._base_url.text().strip(),
            model=self._model.text().strip(),
            use_chat_history=self._use_chat_history.isChecked(),
        )
        try:
            config.validate()
            if config.is_enabled and self._api_key.text().strip():
                self._credentials.set_api_key(config.provider, self._api_key.text().strip())
        except (RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "无法保存设置", str(error))
            return
        self._settings_service.save(AppSettings(ai=config))
        self._api_key.clear()
        if config.is_enabled:
            self._status.setText("设置已保存。聊天功能将在下一阶段接入此配置。")
        else:
            self._status.setText("已切换为普通模式，任务与计时功能不受影响。")

    def _refresh_enabled_state(self) -> None:
        enabled = self._provider.currentData() is not ProviderKind.NONE
        for widget in (self._base_url, self._model, self._api_key, self._use_chat_history):
            widget.setEnabled(enabled)
        if not self._credentials.is_available and enabled:
            self._status.setText("尚未安装 keyring；保存 API Key 前请安装 requirements.txt 中的依赖。")
        elif enabled:
            self._status.setText("可使用 OpenAI、DeepSeek 等兼容服务，或本机 Ollama。")
        else:
            self._status.setText("普通模式不需要 API Key。")

    def test_connection(self) -> None:
        """Test the form's current values without persisting them."""
        if self._test_worker is not None:
            return
        config = AIConfig(
            provider=self._provider.currentData(),
            base_url=self._base_url.text().strip(),
            model=self._model.text().strip(),
        )
        if not config.is_enabled:
            QMessageBox.information(self, "无法测试", "请先选择 AI 服务商。")
            return
        try:
            config.validate()
        except ValueError as error:
            QMessageBox.warning(self, "无法测试", str(error))
            return
        self._status.setText("正在测试当前输入；测试不会保存配置或 API Key…")
        self._test_button.setEnabled(False)
        self._test_worker = ConnectionTestWorker(config, self._api_key.text().strip(), self._credentials)
        self._test_worker.succeeded.connect(self._test_succeeded)
        self._test_worker.failed.connect(self._test_failed)
        self._test_worker.finished.connect(self._test_finished)
        self._test_worker.start()

    def _test_succeeded(self, reply: str) -> None:
        self._status.setText(f"连接成功。服务回复：{reply[:120]}")

    def _test_failed(self, error: str) -> None:
        self._status.setText(f"连接失败：{error}")

    def _test_finished(self) -> None:
        self._test_button.setEnabled(True)
        self._test_worker = None
