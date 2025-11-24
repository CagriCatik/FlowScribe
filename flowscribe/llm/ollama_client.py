"""Ollama LLM client implementation."""
from __future__ import annotations

import requests
from dataclasses import dataclass
from typing import Any

from .base import LLMClient, LLMGenerationOptions, LLMRequest, LLMResult
from .errors import LLMNetworkError, LLMResponseError
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class OllamaConfig:
    host: str
    model: str


class OllamaLLMClient(LLMClient):
    def __init__(self, config: OllamaConfig) -> None:
        self.config = config

    def generate(self, request: LLMRequest, options: LLMGenerationOptions) -> LLMResult:
        url = self.config.host.rstrip("/") + "/api/chat"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
        }

        opts = {
            "num_predict": options.num_predict,
            "temperature": options.temperature,
            "top_p": options.top_p,
            "num_ctx": options.num_ctx,
            "repeat_penalty": options.repeat_penalty,
        }
        opts = {k: v for k, v in opts.items() if v is not None}
        if opts:
            payload["options"] = opts
            logger.debug("Using Ollama generation options: %s", opts)

        try:
            logger.debug("POST %s", url)
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - network issues
            raise LLMNetworkError(f"Failed to call Ollama: {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:  # pragma: no cover - unexpected responses
            raise LLMResponseError(f"Invalid JSON response from Ollama: {exc}") from exc

        message = data.get("message") if isinstance(data, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not content:
            logger.error("Unexpected Ollama response: %s", data)
            raise LLMResponseError("Missing 'message.content' in Ollama response")

        logger.debug("Received %d characters from Ollama", len(content))
        return LLMResult(content=content)
