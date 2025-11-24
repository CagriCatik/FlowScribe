from types import SimpleNamespace
import json

import requests
import pytest

from flowscribe.llm.ollama_client import OllamaLLMClient, OllamaConfig
from flowscribe.llm.base import LLMRequest, LLMGenerationOptions
from flowscribe.llm.errors import LLMResponseError


def test_generate_success(monkeypatch):
    def fake_post(url, json=None, timeout=None):  # type: ignore
        class Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"message": {"content": "ok"}}

        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    client = OllamaLLMClient(OllamaConfig(host="http://localhost", model="m"))
    result = client.generate(LLMRequest(system_prompt="s", user_prompt="u"), LLMGenerationOptions())
    assert result.content == "ok"


def test_generate_bad_response(monkeypatch):
    def fake_post(url, json=None, timeout=None):  # type: ignore
        class Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"unexpected": True}

        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    client = OllamaLLMClient(OllamaConfig(host="http://localhost", model="m"))
    with pytest.raises(LLMResponseError):
        client.generate(LLMRequest(system_prompt="s", user_prompt="u"), LLMGenerationOptions())
