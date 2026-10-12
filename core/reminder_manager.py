"""本地提醒的创建、查询与到点领取。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Reminder:
    id: int
    message: str
    remind_at: str
    notified: bool


class ReminderManager:
    def __init__(self, database_file: Path) -> None:
        self._database_file = database_file

    def add(self, message: str, remind_at: datetime) -> Reminder:
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("提醒内容不能为空")

        created_at = datetime.now().isoformat(timespec="seconds")
        reminder_at = remind_at.isoformat(timespec="seconds")
        with sqlite3.connect(self._database_file) as connection:
            cursor = connection.execute(
                """
                INSERT INTO reminders (message, remind_at, notified, created_at)
                VALUES (?, ?, 0, ?)
                """,
                (clean_message, reminder_at, created_at),
            )
            reminder_id = int(cursor.lastrowid)

        return Reminder(reminder_id, clean_message, reminder_at, False)

    def list_upcoming(self, limit: int = 20) -> list[Reminder]:
        with sqlite3.connect(self._database_file) as connection:
            rows = connection.execute(
                """
                SELECT id, message, remind_at, notified
                FROM reminders
                WHERE notified = 0
                ORDER BY remind_at ASC, id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [Reminder(row[0], row[1], row[2], bool(row[3])) for row in rows]

    def claim_due(self, now: datetime | None = None) -> list[Reminder]:
        """返回到点但尚未处理的提醒。

        名称为兼容已有调用而保留；提醒不会在显示时自动完成，只有用户
        选择完成或稍后提醒后才会改变状态。
        """
        current_time = (now or datetime.now()).isoformat(timespec="seconds")
        with sqlite3.connect(self._database_file) as connection:
            rows = connection.execute(
                """
                SELECT id, message, remind_at, notified
                FROM reminders
                WHERE notified = 0 AND remind_at <= ?
                ORDER BY remind_at ASC, id ASC
                """,
                (current_time,),
            ).fetchall()

        return [Reminder(row[0], row[1], row[2], bool(row[3])) for row in rows]

    def complete(self, reminder_id: int) -> None:
        with sqlite3.connect(self._database_file) as connection:
            connection.execute(
                "UPDATE reminders SET notified = 1 WHERE id = ?",
                (reminder_id,),
            )

    def delete(self, reminder_id: int) -> None:
        with sqlite3.connect(self._database_file) as connection:
            connection.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))

    def snooze(self, reminder_id: int, minutes: int = 10) -> None:
        later = datetime.now() + timedelta(minutes=minutes)
        with sqlite3.connect(self._database_file) as connection:
            connection.execute(
                "UPDATE reminders SET remind_at = ?, notified = 0 WHERE id = ?",
                (later.isoformat(timespec="seconds"), reminder_id),
            )
