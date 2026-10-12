"""Local task persistence without a dependency on the user interface."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Task:
    id: int
    title: str
    category: str
    completed: bool
    created_at: str


class TaskManager:
    def __init__(self, database_file: Path) -> None:
        self._database_file = database_file

    def add_task(self, title: str, category: str = "学习") -> Task:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("任务名称不能为空。")
        created_at = datetime.now().isoformat(timespec="seconds")
        with sqlite3.connect(self._database_file) as connection:
            cursor = connection.execute(
                "INSERT INTO tasks (title, category, created_at) VALUES (?, ?, ?)",
                (clean_title, category, created_at),
            )
            task_id = int(cursor.lastrowid)
        return Task(task_id, clean_title, category, False, created_at)

    def list_tasks(self) -> list[Task]:
        with sqlite3.connect(self._database_file) as connection:
            rows = connection.execute(
                "SELECT id, title, category, completed, created_at "
                "FROM tasks ORDER BY completed ASC, id DESC"
            ).fetchall()
        return [Task(row[0], row[1], row[2], bool(row[3]), row[4]) for row in rows]

    def delete(self, task_id: int) -> None:
        with sqlite3.connect(self._database_file) as connection:
            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def set_completed(self, task_id: int, completed: bool) -> None:
        with sqlite3.connect(self._database_file) as connection:
            connection.execute(
                "UPDATE tasks SET completed = ? WHERE id = ?", (int(completed), task_id)
            )
