"""StudyPet AI application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from ai.provider_manager import ProviderManager
from config.settings_service import SettingsService
from core.app_paths import AppPaths
from pet.pet_window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("StudyPet AI")
    app.setOrganizationName("StudyPet")

    paths = AppPaths.for_current_user()
    paths.ensure_exists()
    settings = SettingsService(paths.settings_file).load()
    # The rest of V0.1 can run in ordinary mode when this has no AI configuration.
    ProviderManager(settings.ai)

    window = PetWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
