"""Persisted AI-provider metadata; API keys never belong in this file."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from urllib.parse import urlparse


class ProviderKind(StrEnum):
    """Provider families supported by the initial configuration contract."""

    NONE = "none"
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"


@dataclass(frozen=True, slots=True)
class AIConfig:
    """Provider information needed to create an AI client in a later release."""

    provider: ProviderKind = ProviderKind.NONE
    base_url: str = ""
    model: str = ""

    @property
    def is_enabled(self) -> bool:
        return self.provider is not ProviderKind.NONE

    def validate(self) -> None:
        """Raise ValueError when an enabled provider lacks usable metadata."""
        if not self.is_enabled:
            return
        if not self.model.strip():
            raise ValueError("AI model is required when an AI provider is enabled.")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("AI base URL must be a complete HTTP or HTTPS URL.")

    def to_dict(self) -> dict[str, str]:
        """Return safe-to-persist fields only; no secret can enter this output."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> "AIConfig":
        """Read untrusted JSON defensively and fall back to no-AI mode."""
        if not isinstance(value, dict):
            return cls()
        try:
            provider = ProviderKind(str(value.get("provider", ProviderKind.NONE)))
        except ValueError:
            return cls()
        return cls(
            provider=provider,
            base_url=str(value.get("base_url", "")),
            model=str(value.get("model", "")),
        )
