"""Local settings persistence with atomic writes and no credential fields."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from config.ai_config import AIConfig


@dataclass(frozen=True, slots=True)
class AppSettings:
    ai: AIConfig = AIConfig()

    def to_dict(self) -> dict[str, object]:
        return {"ai": self.ai.to_dict()}

    @classmethod
    def from_dict(cls, value: object) -> "AppSettings":
        if not isinstance(value, dict):
            return cls()
        return cls(ai=AIConfig.from_dict(value.get("ai")))


class SettingsService:
    """Reads and writes safe application settings for one local user."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def load(self) -> AppSettings:
        if not self._file_path.exists():
            return AppSettings()
        try:
            value = json.loads(self._file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppSettings()
        return AppSettings.from_dict(value)

    def save(self, settings: AppSettings) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(settings.to_dict(), ensure_ascii=False, indent=2)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._file_path.parent,
            prefix=f".{self._file_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(serialized)
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(self._file_path)
