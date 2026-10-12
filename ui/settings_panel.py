"""A local, credential-safe AI configuration panel."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
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
        self._build_ui()
        self.load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        title = QLabel("AI 模型设置")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)
        note = QLabel("API Key 仅保存在 Windows 凭据管理器，不会写入设置文件或数据库。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #52616b; padding: 4px 0 12px;")
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

        self._status = QLabel()
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        save_button = QPushButton("保存 AI 设置")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        layout.addStretch()
        self._provider.currentIndexChanged.connect(self._refresh_enabled_state)

    def load_settings(self) -> None:
        settings = self._settings_service.load()
        index = self._provider.findData(settings.ai.provider)
        self._provider.setCurrentIndex(max(index, 0))
        self._base_url.setText(settings.ai.base_url)
        self._model.setText(settings.ai.model)
        self._api_key.clear()
        self._refresh_enabled_state()

    def save_settings(self) -> None:
        provider = self._provider.currentData()
        config = AIConfig(
            provider=provider,
            base_url=self._base_url.text().strip(),
            model=self._model.text().strip(),
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
        for widget in (self._base_url, self._model, self._api_key):
            widget.setEnabled(enabled)
        if not self._credentials.is_available and enabled:
            self._status.setText("尚未安装 keyring；保存 API Key 前请安装 requirements.txt 中的依赖。")
        elif enabled:
            self._status.setText("可使用 OpenAI、DeepSeek 等兼容服务，或本机 Ollama。")
        else:
            self._status.setText("普通模式不需要 API Key。")
