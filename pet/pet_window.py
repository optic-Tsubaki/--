"""Transparent, draggable, always-on-top StudyPet window."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QGuiApplication, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap, QPolygon
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QLabel, QMenu, QWidget

from pet.pet_controller import PetController, PetState


class PetWindow(QWidget):
    """The small desktop companion shown outside the main dashboard."""

    WINDOW_SIZE = 300
    # A square canvas suits full-body character illustrations and prevents
    # portrait assets from being squeezed into the former shallow rectangle.
    CHARACTER_RECT = QRectF(32, 62, 236, 236)

    def __init__(self, on_open_dashboard: Callable[[str], None] | None = None) -> None:
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
        self._on_open_dashboard = on_open_dashboard
        self._state = PetState.IDLE
        self._frames: list[QPixmap] = []
        self._svg_renderer: QSvgRenderer | None = None
        self._frame_index = 0
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._advance_animation)
        self._idle_phase = 0.0
        self._reaction_token = 0
        self._life_timer = QTimer(self)
        self._life_timer.setInterval(50)
        self._life_timer.timeout.connect(self._advance_idle_motion)
        self._life_timer.start()
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

    def begin_focus_session(self, task_label: str) -> None:
        """Reflect an active productivity session in the desktop companion."""
        self._controller.set_state(PetState.FOCUS)
        self.speak(f"开始专注：{task_label}", duration_ms=3600)

    def show_reminder(self, message: str) -> None:
        self._show_temporary_state(PetState.HAPPY, 5_200)
        self.speak(f"提醒你：{message}")

    def finish_focus_session(self, duration_seconds: int) -> None:
        """Celebrate a saved focus session and return to the idle companion."""
        minutes = max(1, duration_seconds // 60)
        self._show_temporary_state(PetState.CELEBRATE, 2_600, return_state=PetState.IDLE)
        self.speak(f"完成啦！这次专注了 {minutes} 分钟。", duration_ms=4200)

    def complete_task(self, task_label: str) -> None:
        """Celebrate a checked-off task without interrupting an active focus state."""
        self._show_temporary_state(PetState.CELEBRATE, 2_400)
        self.speak(f"完成「{task_label}」！做得漂亮。", duration_ms=3_200)

    def greet(self) -> None:
        """Give a short visual acknowledgement before opening the control panel."""
        self._show_temporary_state(PetState.GREETING, 1_600)
        self.speak("我在，今天也一起稳稳推进。", duration_ms=2_600)

    def _set_state(self, state: PetState) -> None:
        """Apply a persistent state and cancel any earlier temporary reaction."""
        self._reaction_token += 1
        self._apply_state(state)

    def _apply_state(self, state: PetState) -> None:
        self._state = state
        # Interaction-only states intentionally borrow a real animated state:
        # a greeting keeps the quiet idle loop, while a completed task plays
        # the dedicated happy jump frames.
        asset_state = {
            PetState.GREETING: PetState.IDLE,
            PetState.CELEBRATE: PetState.HAPPY,
        }.get(state, state)
        self._load_character_frames(asset_state)
        self.update()

    def _show_temporary_state(
        self,
        state: PetState,
        duration_ms: int,
        *,
        return_state: PetState | None = None,
    ) -> None:
        """Play an expressive action, then restore the previous working state."""
        restore_state = return_state or self._state
        self._reaction_token += 1
        token = self._reaction_token
        self._apply_state(state)

        def restore() -> None:
            if token == self._reaction_token:
                self._apply_state(restore_state)

        QTimer.singleShot(duration_ms, restore)

    def _load_character_frames(self, state: PetState) -> None:
        """Load a vector idle image or ordered PNG frames for a state."""
        images_dir = Path(__file__).parent.parent / "resources" / "images"
        project_root = images_dir.parent.parent
        vector_idle = project_root / "图片" / "霓虹狐耳 chibi 少女贴纸.svg"

        current_renderer = self._svg_renderer

        def load_vector_idle() -> bool:
            if current_renderer is not None and current_renderer.isValid():
                self._frames = []
                self._frame_index = 0
                self._svg_renderer = current_renderer
                self._animation_timer.stop()
                return True
            if not vector_idle.exists():
                return False
            renderer = QSvgRenderer(str(vector_idle), self)
            if not renderer.isValid():
                return False
            self._frames = []
            self._frame_index = 0
            self._svg_renderer = renderer
            self._animation_timer.stop()
            return True

        self._svg_renderer = None
        # State-specific PNG frame sequences take priority.  The original SVG
        # remains a crisp fallback when a release is missing its art assets.
        candidates: list[list[Path]] = []
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
        if not self._frames and load_vector_idle():
            return
        self._frame_index = 0
        if len(self._frames) > 1:
            # Slower breathing/sleep cycles, with quicker feedback for focus
            # and happy actions, keep the pixel animation readable.
            self._animation_timer.start(
                440 if state in {PetState.IDLE, PetState.SLEEP} else 240
            )
        else:
            self._animation_timer.stop()

    def _advance_animation(self) -> None:
        if not self._frames:
            self._animation_timer.stop()
            return
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.update()

    def _advance_idle_motion(self) -> None:
        """Drive small state-specific vector motions without a sprite sheet."""
        if self._svg_renderer is not None:
            self._idle_phase = (self._idle_phase + 0.11) % math.tau
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
                try:
                    self.greet()
                except Exception:
                    # A cosmetic response must never be able to close the pet.
                    self._set_state(PetState.IDLE)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_dashboard("home")
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

    def _show_quick_menu(self, position: QPoint) -> None:
        """Show the V0.1 shortcuts promised by the desktop-pet interaction."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #fefcff; border: 1px solid #b8d9ca; border-radius: 10px; "
            "padding: 6px; font-family: 'Microsoft YaHei UI'; } "
            "QMenu::item { padding: 8px 28px 8px 12px; border-radius: 6px; } "
            "QMenu::item:selected { background: #dff6e9; }"
        )
        greeting = menu.addAction("今天也一起努力吧！")
        greeting.setEnabled(False)
        menu.addSeparator()

        chat_action = menu.addAction("聊天")
        chat_action.triggered.connect(lambda: self._open_dashboard("chat"))
        if self._on_open_dashboard is not None:
            self._on_open_dashboard("home")
        return

        for label, section in (
            ("今日任务", "tasks"),
            ("开始计时", "timer"),
            ("学习统计", "stats"),
        ):
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, value=section: self._open_dashboard(value))
        settings_action = menu.addAction("设置")
        settings_action.triggered.connect(lambda: self._open_dashboard("settings"))
        menu.exec(position)

    def _open_dashboard(self, section: str) -> None:
        if self._on_open_dashboard is None:
            self.speak("控制面板尚未准备好。")
            return
        self._on_open_dashboard(section)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._svg_renderer is not None:
            self._draw_vector_character(painter)
        elif self._frames:
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

    def _draw_vector_character(self, painter: QPainter) -> None:
        """Render the vector pet with small, readable state-specific actions."""
        assert self._svg_renderer is not None
        center_x = self.CHARACTER_RECT.center().x()
        baseline_y = self.CHARACTER_RECT.bottom()
        phase = self._idle_phase
        breathing = math.sin(phase)
        scale_x, scale_y = 0.86, 1.15
        vertical_offset = 0.0
        rotation = 0.0

        if self._state is PetState.IDLE:
            vertical_offset = 1.5 * breathing
            scale_x *= 1.0 + 0.006 * breathing
            scale_y *= 1.0 - 0.008 * breathing
        elif self._state is PetState.FOCUS:
            # A steadier, slightly forward pose communicates that the pet is working.
            vertical_offset = 0.7 * math.sin(phase * 0.65)
            scale_x *= 0.985
            scale_y *= 1.025
        elif self._state is PetState.HAPPY:
            # A reminder should be noticeable without competing with the artwork.
            vertical_offset = -3.0 * abs(math.sin(phase * 1.3))
            scale_x *= 1.0 + 0.006 * abs(math.sin(phase * 1.3))
        elif self._state is PetState.GREETING:
            # A small nod reads more naturally for this compact chibi illustration.
            vertical_offset = -1.5 * abs(math.sin(phase * 1.45))
            rotation = 1.2 * math.sin(phase * 1.45)
        elif self._state is PetState.CELEBRATE:
            # A single light hop is enough to mark a genuine achievement.
            vertical_offset = -6.0 * abs(math.sin(phase * 1.45))
            scale_x *= 1.0 + 0.012 * abs(math.sin(phase * 1.45))
            scale_y *= 1.0 - 0.009 * abs(math.sin(phase * 1.45))
        elif self._state is PetState.SLEEP:
            vertical_offset = 2.0 + 1.2 * math.sin(phase * 0.55)
            scale_x *= 0.97
            scale_y *= 0.985

        painter.save()
        painter.translate(center_x, baseline_y + vertical_offset)
        painter.rotate(rotation)
        painter.scale(scale_x, scale_y)
        painter.translate(-center_x, -baseline_y)
        self._svg_renderer.render(painter, self.CHARACTER_RECT)
        if self._state in {PetState.HAPPY, PetState.CELEBRATE}:
            self._draw_celebrating_sleeves(painter, phase)
        painter.restore()

    def _draw_celebrating_sleeves(self, painter: QPainter, phase: float) -> None:
        """Animate the original sleeves as separate vector cut-outs for celebration.

        The supplied SVG is a flattened trace, so it has no editable arm layers.
        These two carefully placed crop regions reuse the exact original artwork
        while pivoting around each shoulder; no generated or redrawn character
        art is introduced.
        """
        assert self._svg_renderer is not None
        left_sleeve = QRectF(48, 166, 72, 94)
        right_sleeve = QRectF(180, 166, 72, 94)
        motion = 3.0 * math.sin(phase * 1.45)
        strength = 42.0 if self._state is PetState.CELEBRATE else 20.0

        for sleeve, pivot, angle in (
            (left_sleeve, QPoint(109, 181), -strength + motion),
            (right_sleeve, QPoint(191, 181), strength - motion),
        ):
            # Remove the resting sleeve before redrawing the same original
            # pixels at its raised pose.  The clear area stays transparent.
            painter.save()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(sleeve.adjusted(-2, -2, 2, 2), Qt.GlobalColor.transparent)
            painter.restore()

            painter.save()
            painter.translate(pivot)
            painter.rotate(angle)
            painter.translate(-pivot)
            painter.setClipRect(sleeve)
            self._svg_renderer.render(painter, self.CHARACTER_RECT)
            painter.restore()

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
