"""置顶且需要明确处理的学习提醒卡片。"""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ReminderDialog(QDialog):
    def __init__(
        self,
        message: str,
        on_complete: Callable[[], None],
        on_snooze: Callable[[], None],
    ) -> None:
        super().__init__(None)
        self._on_complete = on_complete
        self._on_snooze = on_snooze

        self.setWindowTitle("StudyPet · 学习提醒")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setMinimumWidth(390)
        self.setStyleSheet(
            """
            QDialog { background: #152725; color: #f4f5ed; }
            QWidget#card { background: #203936; border: 1px solid #4f8176; border-radius: 20px; }
            QLabel#eyebrow { color: #aeead5; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
            QLabel#title { color: #f8f4e8; font-size: 22px; font-weight: 700; }
            QLabel#message { color: #e1ebe7; font-size: 15px; line-height: 1.45; }
            QLabel#note { color: #9dbcb4; font-size: 12px; }
            QPushButton { border-radius: 11px; padding: 10px 17px; font-weight: 700; }
            QPushButton#snooze { background: transparent; border: 1px solid #67978b; color: #c9e5dc; }
            QPushButton#complete { background: #b8ed70; border: 1px solid #d5fb9a; color: #17312c; }
            QPushButton#complete:hover { background: #d0f88c; }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        card = QWidget()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        eyebrow = QLabel("●  STUDYPET  ·  待处理提醒")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("现在该处理这件事了")
        title.setObjectName("title")
        message_label = QLabel(message)
        message_label.setObjectName("message")
        message_label.setWordWrap(True)
        note = QLabel("提醒会保持显示，直到你选择完成或稍后提醒。")
        note.setObjectName("note")
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(message_label)
        layout.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch()
        snooze = QPushButton("10 分钟后")
        snooze.setObjectName("snooze")
        snooze.clicked.connect(self._snooze)
        complete = QPushButton("我已处理")
        complete.setObjectName("complete")
        complete.clicked.connect(self._complete)
        buttons.addWidget(snooze)
        buttons.addWidget(complete)
        layout.addLayout(buttons)
        outer.addWidget(card)

    def _complete(self) -> None:
        self._on_complete()
        self.accept()

    def _snooze(self) -> None:
        self._on_snooze()
        self.accept()

    def reject(self) -> None:
        """Esc 和窗口关闭键不应绕过提醒处理。"""
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.raise_()
        self.activateWindow()
