"""Abstract LLM client interface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class LLMRequest:
    system_prompt: str
    user_prompt: str


@dataclass(slots=True)
class LLMResult:
    content: str


@dataclass(slots=True)
class LLMGenerationOptions:
    num_predict: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    num_ctx: int | None = None
    repeat_penalty: float | None = None


class LLMClient(Protocol):
    """Protocol for LLM backends."""

    def generate(self, request: LLMRequest, options: LLMGenerationOptions) -> LLMResult:
        ...
