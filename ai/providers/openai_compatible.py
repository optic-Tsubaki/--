"""A small dependency-free client for OpenAI-compatible chat endpoints."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai.providers.base import AIProvider, ChatMessage


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._api_key = api_key

    def chat(self, messages: list[ChatMessage]) -> str:
        body = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": item.role, "content": item.content} for item in messages],
            }
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"AI 服务返回 HTTP {error.code}：{detail}") from error
        except URLError as error:
            raise RuntimeError(f"无法连接 AI 服务：{error.reason}") from error
        try:
            return str(payload["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("AI 服务返回了无法识别的响应格式。") from error
