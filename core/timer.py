"""A local focus timer that records completed sessions in SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class FocusTimer:
    def __init__(self, database_file: Path) -> None:
        self._database_file = database_file
        self._started_at: datetime | None = None
        self._task_id: int | None = None

    @property
    def is_running(self) -> bool:
        return self._started_at is not None

    def start(self, task_id: int | None = None) -> None:
        if self.is_running:
            return
        self._started_at = datetime.now()
        self._task_id = task_id

    def elapsed_seconds(self) -> int:
        if self._started_at is None:
            return 0
        return max(0, int((datetime.now() - self._started_at).total_seconds()))

    def stop(self) -> int:
        if self._started_at is None:
            return 0
        started_at = self._started_at
        duration = self.elapsed_seconds()
        with sqlite3.connect(self._database_file) as connection:
            connection.execute(
                "INSERT INTO study_sessions (task_id, started_at, duration_seconds) VALUES (?, ?, ?)",
                (self._task_id, started_at.isoformat(timespec="seconds"), duration),
            )
        self._started_at = None
        self._task_id = None
        return duration

    def total_today_seconds(self) -> int:
        today = datetime.now().date().isoformat()
        with sqlite3.connect(self._database_file) as connection:
            stored = connection.execute(
                "SELECT COALESCE(SUM(duration_seconds), 0) FROM study_sessions "
                "WHERE substr(started_at, 1, 10) = ?",
                (today,),
            ).fetchone()[0]
        return int(stored) + self.elapsed_seconds()
