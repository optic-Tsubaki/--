"""Select an available provider without making the rest of the app vendor-aware."""

from __future__ import annotations

from ai.providers.base import AIProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.openai_compatible import OpenAICompatibleProvider
from config.ai_config import AIConfig
from config.ai_config import ProviderKind
from security.credential_store import CredentialStore


class ProviderManager:
    """Owns provider selection; clients will be registered in a later phase."""

    def __init__(self, config: AIConfig, credentials: CredentialStore | None = None) -> None:
        self._config = config
        self._credentials = credentials

    @property
    def is_configured(self) -> bool:
        """Whether the user enabled an AI provider in their local settings."""
        return self._config.is_enabled

    def describe_status(self) -> str:
        if not self.is_configured:
            return "AI 未配置，StudyPet 正在普通模式下运行。"
        return f"AI 已配置：{self._config.provider} / {self._config.model}"

    def create_provider(self) -> AIProvider:
        """Create only the provider selected by the user, never a hard-coded one."""
        self._config.validate()
        if self._config.provider is ProviderKind.OLLAMA:
            return OllamaProvider(self._config.base_url, self._config.model)
        if self._config.provider is ProviderKind.OPENAI_COMPATIBLE:
            if self._credentials is None:
                raise RuntimeError("AI 凭据管理器不可用。")
            api_key = self._credentials.get_api_key(self._config.provider)
            if not api_key:
                raise RuntimeError("请先在“设置”中保存 API Key。")
            return OpenAICompatibleProvider(self._config.base_url, self._config.model, api_key)
        raise RuntimeError("当前处于普通模式，请先在“设置”中配置 AI 服务。")
