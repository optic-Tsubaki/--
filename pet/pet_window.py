"""Transparent, draggable, always-on-top StudyPet window."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QGuiApplication, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap, QPolygon
from PyQt6.QtWidgets import QLabel, QMenu, QWidget

from pet.pet_controller import PetController, PetState


class PetWindow(QWidget):
    """The small desktop companion shown outside the main dashboard."""

    WINDOW_SIZE = 300
    # A square canvas suits full-body character illustrations and prevents
    # portrait assets from being squeezed into the former shallow rectangle.
    CHARACTER_RECT = QRectF(32, 62, 236, 236)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(self.WINDOW_SIZE, self.WINDOW_SIZE)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self._drag_offset: QPoint | None = None
        self._dragged = False
        self._state = PetState.IDLE
        self._frames: list[QPixmap] = []
        self._frame_index = 0
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._advance_animation)
        self._load_character_frames(PetState.IDLE)
        self._controller = PetController(self._set_state, self.speak)

        self._bubble = QLabel(self)
        self._bubble.setWordWrap(True)
        self._bubble.setFixedWidth(214)
        self._bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bubble.setStyleSheet(
            "QLabel { background: rgba(255, 255, 255, 242); color: #39465e; "
            "border: 2px solid #f2b6ca; border-radius: 16px; padding: 9px 12px; "
            "font-size: 13px; font-family: 'Microsoft YaHei UI'; }"
        )
        self._bubble.move(42, 8)
        self._bubble.hide()

        self._bubble_timer = QTimer(self)
        self._bubble_timer.setSingleShot(True)
        self._bubble_timer.timeout.connect(self._bubble.hide)

        self.move_to_bottom_right()

    def move_to_bottom_right(self) -> None:
        """Place the pet near the primary screen's lower-right corner."""
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 24, area.bottom() - self.height() - 24)

    def speak(self, message: str, duration_ms: int = 4200) -> None:
        """Show a temporary speech bubble above the character."""
        self._bubble.setText(message)
        self._bubble.adjustSize()
        self._bubble.move((self.width() - self._bubble.width()) // 2, 8)
        self._bubble.show()
        self._bubble.raise_()
        self._bubble_timer.start(duration_ms)

    def _set_state(self, state: PetState) -> None:
        self._state = state
        self._load_character_frames(state)
        self.update()

    def _load_character_frames(self, state: PetState) -> None:
        """Load ordered PNG frames for a state and start their animation loop."""
        images_dir = Path(__file__).parent.parent / "resources" / "images"
        project_root = images_dir.parent.parent
        vector_idle = project_root / "图片" / "霓虹狐耳 chibi 少女贴纸.svg"

        # Use the supplied vector character for the main idle state. PNG frames
        # remain available for animation states and as a portable fallback.
        candidates: list[list[Path]] = []
        if state is PetState.IDLE and vector_idle.exists():
            candidates.append([vector_idle])

        png_frames = sorted(images_dir.glob(f"{state}_*.png"))
        if png_frames:
            candidates.append(png_frames)
        else:
            single_frame = images_dir / f"{state}.png"
            if single_frame.exists():
                candidates.append([single_frame])

        self._frames = []
        for frame_paths in candidates:
            loaded_frames = [QPixmap(str(path)) for path in frame_paths]
            loaded_frames = [frame for frame in loaded_frames if not frame.isNull()]
            if loaded_frames:
                self._frames = loaded_frames
                break
        self._frame_index = 0
        if len(self._frames) > 1:
            self._animation_timer.start(260)
        else:
            self._animation_timer.stop()

    def _advance_animation(self) -> None:
        if not self._frames:
            self._animation_timer.stop()
            return
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragged = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            self._dragged = True
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if not self._dragged:
                self._controller.set_state(PetState.HAPPY)
                self._controller.speak("你好！今天也一起努力吧！")
                QTimer.singleShot(1800, lambda: self._controller.set_state(PetState.IDLE))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.speak("控制面板会在 V0.2 到来：任务、计时和统计。")
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _show_context_menu(self, event: QMouseEvent) -> None:
        menu = QMenu(self)
        for state, label in (
            (PetState.IDLE, "待机"),
            (PetState.FOCUS, "专注"),
            (PetState.HAPPY, "开心"),
            (PetState.SLEEP, "休息"),
        ):
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, value=state: self._controller.set_state(value))
            menu.addAction(action)
        menu.addSeparator()
        hide_action = menu.addAction("隐藏")
        hide_action.triggered.connect(self.hide)
        exit_action = menu.addAction("退出 StudyPet")
        exit_action.triggered.connect(self.close)
        menu.exec(event.globalPosition().toPoint())

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._frames:
            self._draw_character_frame(painter, self._frames[self._frame_index])
        else:
            self._paint_fallback_cat(painter)

    def _draw_character_frame(self, painter: QPainter, frame: QPixmap) -> None:
        """Draw a frame at its natural aspect ratio, aligned to the baseline."""
        target = self.CHARACTER_RECT.toRect()
        scaled = frame.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            # Desktop pets are small; preserve the strong ink edges instead of
            # blurring the illustration during downscaling.
            Qt.TransformationMode.FastTransformation,
        )
        x = target.x() + (target.width() - scaled.width()) // 2
        y = target.bottom() - scaled.height() + 1
        painter.drawPixmap(x, y, scaled)

    def _paint_fallback_cat(self, painter: QPainter) -> None:
        """A visible starter mascot while the project awaits character PNGs."""
        rect = self.CHARACTER_RECT
        outline = QPen(QColor("#714f68"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(outline)

        # Body and head keep the prototype immediately usable without art assets.
        painter.setBrush(QColor("#f7c9d8"))
        painter.drawEllipse(QRectF(rect.left() + 35, rect.top() + 67, 122, 102))

        head = QPainterPath()
        head.moveTo(rect.left() + 43, rect.top() + 78)
        head.lineTo(rect.left() + 53, rect.top() + 19)
        head.lineTo(rect.left() + 85, rect.top() + 45)
        head.cubicTo(rect.left() + 103, rect.top() + 35, rect.left() + 128, rect.top() + 35, rect.left() + 145, rect.top() + 45)
        head.lineTo(rect.left() + 177, rect.top() + 19)
        head.lineTo(rect.left() + 187, rect.top() + 78)
        head.cubicTo(rect.left() + 188, rect.top() + 140, rect.left() + 42, rect.top() + 140, rect.left() + 43, rect.top() + 78)
        painter.drawPath(head)

        painter.setBrush(QColor("#f59bb9"))
        painter.drawPolygon(QPolygon([
            QPoint(int(rect.left() + 56), int(rect.top() + 34)),
            QPoint(int(rect.left() + 62), int(rect.top() + 66)),
            QPoint(int(rect.left() + 77), int(rect.top() + 49)),
        ]))
        painter.drawPolygon(QPolygon([
            QPoint(int(rect.left() + 174), int(rect.top() + 34)),
            QPoint(int(rect.left() + 168), int(rect.top() + 66)),
            QPoint(int(rect.left() + 153), int(rect.top() + 49)),
        ]))

        painter.setPen(QPen(QColor("#4c3c54"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self._state == PetState.SLEEP:
            painter.drawLine(int(rect.left() + 75), int(rect.top() + 88), int(rect.left() + 95), int(rect.top() + 88))
            painter.drawLine(int(rect.left() + 137), int(rect.top() + 88), int(rect.left() + 157), int(rect.top() + 88))
        else:
            painter.setBrush(QColor("#4c3c54"))
            painter.drawEllipse(QRectF(rect.left() + 76, rect.top() + 77, 17, 24))
            painter.drawEllipse(QRectF(rect.left() + 137, rect.top() + 77, 17, 24))

        painter.setBrush(QColor("#e76f94"))
        painter.drawEllipse(QRectF(rect.left() + 108, rect.top() + 101, 14, 10))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(rect.left() + 93, rect.top() + 103, 44, 29), 205 * 16, 130 * 16)

        painter.setPen(QPen(QColor("#714f68"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(rect.left() + 76), int(rect.top() + 154), int(rect.left() + 65), int(rect.top() + 174))
        painter.drawLine(int(rect.left() + 155), int(rect.top() + 154), int(rect.left() + 166), int(rect.top() + 174))

        painter.setPen(QPen(QColor("#6278bd"), 3))
        painter.drawText(QRectF(48, 270, 204, 22), Qt.AlignmentFlag.AlignCenter, "StudyPet AI")
