"""StudyPet AI application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from ai.provider_manager import ProviderManager
from config.settings_service import SettingsService
from core.app_paths import AppPaths
from core.runtime_logging import configure_runtime_logging
from core.task_manager import TaskManager
from core.reminder_manager import ReminderManager
from core.timer import FocusTimer
from database.sqlite import StudyPetDatabase
from pet.pet_window import PetWindow
from security.credential_store import CredentialStore
from ui.dashboard import Dashboard


def application_root() -> Path:
    """Return the source root in development and the executable folder when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("StudyPet AI")
    app.setOrganizationName("StudyPet")

    paths = AppPaths.for_project(application_root())
    paths.ensure_exists()
    configure_runtime_logging(paths.logs_dir)
    StudyPetDatabase(paths.database_file)
    settings_service = SettingsService(paths.settings_file)
    settings = settings_service.load()
    # The rest of V0.1 can run in ordinary mode when this has no AI configuration.
    ProviderManager(settings.ai)

    task_manager = TaskManager(paths.database_file)
    focus_timer = FocusTimer(paths.database_file)
    window: PetWindow | None = None

    def focus_started(task_label: str) -> None:
        if window is not None:
            window.begin_focus_session(task_label)

    def focus_finished(duration_seconds: int) -> None:
        if window is not None:
            window.finish_focus_session(duration_seconds)

    def reminder_due(message: str) -> None:
        if window is not None:
            window.show_reminder(message)

    dashboard = Dashboard(
        task_manager,
        focus_timer,
        ReminderManager(paths.database_file),
        settings_service,
        CredentialStore(),
        on_focus_started=focus_started,
        on_focus_finished=focus_finished,
        on_reminder_due=reminder_due,
    )
    def open_dashboard(section: str) -> None:
        if section == "home":
            dashboard.open_home()
            return
        dashboard.open_section(section)

    window = PetWindow(on_open_dashboard=open_dashboard)
    window.show()

    tray = QSystemTrayIcon(
        app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon),
        app,
    )
    tray.setToolTip("StudyPet AI · 学习桌宠")
    tray_menu = QMenu()
    open_dashboard_action = tray_menu.addAction("打开控制面板")
    toggle_pet_action = tray_menu.addAction("隐藏桌宠")
    tray_menu.addSeparator()
    quit_action = tray_menu.addAction("退出 StudyPet")

    open_dashboard_action.triggered.connect(dashboard.open_home)

    def toggle_pet() -> None:
        if window is None:
            return
        if window.isVisible():
            window.hide()
            toggle_pet_action.setText("显示桌宠")
        else:
            window.show()
            window.raise_()
            window.activateWindow()
            toggle_pet_action.setText("隐藏桌宠")

    def on_tray_activated(reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            dashboard.open_home()

    toggle_pet_action.triggered.connect(toggle_pet)
    quit_action.triggered.connect(app.quit)
    tray.activated.connect(on_tray_activated)
    tray.setContextMenu(tray_menu)
    # Keep a Python reference for the full application lifetime, then show it
    # after Qt's event loop has started so Windows Explorer can register it.
    app.study_pet_tray = tray  # type: ignore[attr-defined]
    QTimer.singleShot(0, tray.show)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
