"""Tests for Ollama model routing (parse vs chat)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.integrations.ollama.client import OllamaClient


def _mock_chat_response(content: str) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"message": {"content": content}}
    response.raise_for_status = MagicMock()
    return response


def _mock_async_client(post_return: MagicMock) -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=post_return)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def test_model_for_falls_back_to_default():
    s = Settings(ollama_model="llama3.2", ollama_model_parse="", ollama_model_chat="")
    assert s.ollama_model_for("parse") == "llama3.2"
    assert s.ollama_model_for("chat") == "llama3.2"
    assert s.ollama_routing_active is False


def test_model_for_uses_role_overrides():
    s = Settings(
        ollama_model="llama3.2",
        ollama_model_parse="qwen2.5-coder:7b",
        ollama_model_chat="qwen2.5:14b",
    )
    assert s.ollama_model_for("parse") == "qwen2.5-coder:7b"
    assert s.ollama_model_for("chat") == "qwen2.5:14b"
    assert s.ollama_routing_active is True


def test_chat_timeout_override():
    s = Settings(ollama_timeout_seconds=60, ollama_chat_timeout_seconds=180)
    assert s.ollama_timeout_for("parse") == 60.0
    assert s.ollama_timeout_for("chat") == 180.0


@pytest.mark.asyncio
async def test_generate_text_uses_chat_model():
    settings = Settings(
        ollama_model="llama3.2",
        ollama_model_chat="qwen2.5:14b",
        monsoon_soul_prompt="soul",
    )
    client = OllamaClient(settings)
    mock_http = _mock_async_client(_mock_chat_response("hello"))

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        await client.generate_text(user_prompt="hi", purpose="chat")

    assert mock_http.post.call_args.kwargs["json"]["model"] == "qwen2.5:14b"


@pytest.mark.asyncio
async def test_parse_uses_parse_model():
    settings = Settings(
        ollama_model="llama3.2",
        ollama_model_parse="qwen2.5-coder:7b",
    )
    client = OllamaClient(settings)
    mock_http = _mock_async_client(
        _mock_chat_response('{"kind":"todo","title":"x","notes":null,'
                            '"task_number":null,"due_at":null,"remind_at":null,'
                            '"status":null,"priority":null}')
    )

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        await client.parse_capture("todo buy milk", "2026-07-12T10:00:00+02:00")

    assert mock_http.post.call_args.kwargs["json"]["model"] == "qwen2.5-coder:7b"
