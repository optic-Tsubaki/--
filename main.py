"""StudyPet AI application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from pet.pet_window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("StudyPet AI")
    app.setOrganizationName("StudyPet")

    window = PetWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
