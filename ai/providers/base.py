"""Provider-neutral contracts for the later chat implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


class AIProvider(ABC):
    """The interface used by a future agent, independent of model vendor."""

    @abstractmethod
    def chat(self, messages: list[ChatMessage]) -> str:
        """Return a completed assistant reply for the supplied conversation."""
