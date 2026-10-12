"""Client for an Ollama server running on the user's own computer."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.providers.base import AIProvider, ChatMessage


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/api/chat"
        self._model = model

    def chat(self, messages: list[ChatMessage]) -> str:
        body = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": item.role, "content": item.content} for item in messages],
                "stream": False,
            }
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"Ollama 返回 HTTP {error.code}：{detail}") from error
        except URLError as error:
            raise RuntimeError(f"无法连接 Ollama：{error.reason}") from error
        try:
            return str(payload["message"]["content"]).strip()
        except (KeyError, TypeError) as error:
            raise RuntimeError("Ollama 返回了无法识别的响应格式。") from error
