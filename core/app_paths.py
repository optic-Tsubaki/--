"""Stable writable locations for a packaged or source checkout of StudyPet."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "StudyPet"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """The directories owned by the current StudyPet user."""

    root: Path
    settings_file: Path
    database_file: Path
    logs_dir: Path

    @classmethod
    def for_current_user(cls) -> "AppPaths":
        """Return Windows-friendly paths without writing anything yet."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        root = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        root = root / APP_NAME
        return cls(
            root=root,
            settings_file=root / "settings.json",
            database_file=root / "studypet.db",
            logs_dir=root / "logs",
        )

    def ensure_exists(self) -> None:
        """Create only the application's writable directories."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
