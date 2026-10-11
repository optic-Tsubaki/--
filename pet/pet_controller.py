"""A small, UI-independent control surface for future StudyPet features."""

from __future__ import annotations

from enum import StrEnum
from typing import Callable


class PetState(StrEnum):
    """Visual states supported by the first desktop-pet prototype."""

    IDLE = "idle"
    HAPPY = "happy"
    SLEEP = "sleep"
    FOCUS = "focus"


class PetController:
    """Coordinates state and speech without coupling future modules to Qt."""

    def __init__(
        self,
        on_state_changed: Callable[[PetState], None],
        on_speak: Callable[[str], None],
    ) -> None:
        self._state = PetState.IDLE
        self._on_state_changed = on_state_changed
        self._on_speak = on_speak

    @property
    def state(self) -> PetState:
        return self._state

    def set_state(self, state: PetState) -> None:
        self._state = state
        self._on_state_changed(state)

    def speak(self, message: str) -> None:
        self._on_speak(message)
