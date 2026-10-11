"""Select an available provider without making the rest of the app vendor-aware."""

from __future__ import annotations

from config.ai_config import AIConfig


class ProviderManager:
    """Owns provider selection; clients will be registered in a later phase."""

    def __init__(self, config: AIConfig) -> None:
        self._config = config

    @property
    def is_configured(self) -> bool:
        """Whether the user enabled an AI provider in their local settings."""
        return self._config.is_enabled

    def describe_status(self) -> str:
        if not self.is_configured:
            return "AI 未配置，StudyPet 正在普通模式下运行。"
        return f"AI 已配置：{self._config.provider} / {self._config.model}"
