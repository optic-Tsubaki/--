"""本地 AI 聊天记录存储。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ChatHistoryItem:
    role: str
    content: str
    created_at: str


class ChatHistory:
    def __init__(self, database_file: Path) -> None:
        self._database_file = database_file

    def add(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("聊天角色无效")
        clean_content = content.strip()
        if not clean_content:
            return
        with sqlite3.connect(self._database_file) as connection:
            connection.execute(
                """
                INSERT INTO chat_messages (role, content, created_at)
                VALUES (?, ?, ?)
                """,
                (role, clean_content, datetime.now().isoformat(timespec="seconds")),
            )

    def recent(self, limit: int = 24) -> list[ChatHistoryItem]:
        with sqlite3.connect(self._database_file) as connection:
            rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM (
                    SELECT id, role, content, created_at
                    FROM chat_messages
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (limit,),
            ).fetchall()
        return [ChatHistoryItem(*row) for row in rows]

    def clear(self) -> None:
        with sqlite3.connect(self._database_file) as connection:
            connection.execute("DELETE FROM chat_messages")

    def remove_latest(self, role: str, content: str) -> None:
        """撤销发送失败的最后一条临时用户消息。"""
        with sqlite3.connect(self._database_file) as connection:
            connection.execute(
                """
                DELETE FROM chat_messages
                WHERE id = (
                    SELECT id FROM chat_messages
                    WHERE role = ? AND content = ?
                    ORDER BY id DESC
                    LIMIT 1
                )
                """,
                (role, content),
            )
