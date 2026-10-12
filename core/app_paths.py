"""Stable writable locations for a packaged or source checkout of StudyPet."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "StudyPet"


@dataclass(frozen=True, slots=True)
class AppPaths:
    @classmethod
    def for_project(cls, project_root: Path) -> "AppPaths":
        """将可变数据与项目放在一起，便于整体备份和迁移。"""
        root = project_root / "data"
        return cls(
            root=root,
            settings_file=root / "settings.json",
            records_dir=root / "records",
            database_file=root / "records" / "studypet.db",
            logs_dir=root / "logs",
        )

    """The directories owned by the current StudyPet user."""

    root: Path
    settings_file: Path
    records_dir: Path
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
            records_dir=root / "records",
            database_file=root / "records" / "studypet.db",
            logs_dir=root / "logs",
        )

    def ensure_exists(self) -> None:
        """Create only the application's writable directories."""
        self.root.mkdir(parents=True, exist_ok=True)
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        legacy_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "StudyPet"
        legacy_settings = legacy_root / "settings.json"
        legacy_database = legacy_root / "records" / "studypet.db"
        if legacy_settings.exists() and not self.settings_file.exists():
            shutil.copy2(legacy_settings, self.settings_file)
        if legacy_database.exists() and not self.database_file.exists():
            shutil.copy2(legacy_database, self.database_file)
        legacy_database = self.root / "studypet.db"
        if legacy_database.exists() and not self.database_file.exists():
            shutil.move(str(legacy_database), str(self.database_file))
