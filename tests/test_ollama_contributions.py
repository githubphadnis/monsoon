"""Tests for Ollama contribution generation (digest, reflect)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import Settings
from app.integrations.ollama.client import (
    DIGEST_INSTRUCTION,
    OllamaClient,
    PARSE_PROMPT,
)


def _mock_chat_response(content: str) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"message": {"content": content}}
    response.raise_for_status = MagicMock()
    return response


def _mock_async_client(post_return: MagicMock | Exception) -> AsyncMock:
    mock_client = AsyncMock()
    if isinstance(post_return, Exception):
        mock_client.post = AsyncMock(side_effect=post_return)
    else:
        mock_client.post = AsyncMock(return_value=post_return)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_generate_text_returns_content_on_success():
    settings = Settings(monsoon_soul_prompt="You are monsoon, concise assistant.")
    client = OllamaClient(settings)
    mock_response = _mock_chat_response("Here is your summary.")

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=_mock_async_client(mock_response),
    ):
        result = await client.generate_text(user_prompt="Summarize my day")

    assert result == "Here is your summary."


@pytest.mark.asyncio
async def test_generate_text_uses_soul_prompt_by_default():
    settings = Settings(monsoon_soul_prompt="Soul prompt for monsoon")
    client = OllamaClient(settings)
    mock_response = _mock_chat_response("ok")
    mock_http = _mock_async_client(mock_response)

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        await client.generate_text(user_prompt="hello")

    payload = mock_http.post.call_args.kwargs["json"]
    assert payload["messages"][0]["content"] == "Soul prompt for monsoon"
    assert "format" not in payload
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_generate_digest_includes_soul_and_digest_instruction():
    settings = Settings(monsoon_soul_prompt="Soul prompt for monsoon")
    client = OllamaClient(settings)
    mock_response = _mock_chat_response("Today: finish report. Next: call bank.")
    mock_http = _mock_async_client(mock_response)

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        result = await client.generate_digest(
            context_text="- Task A\n- Task B",
            now_iso="2026-07-08T10:00:00+02:00",
        )

    assert result == "Today: finish report. Next: call bank."
    payload = mock_http.post.call_args.kwargs["json"]
    system_content = payload["messages"][0]["content"]
    assert "Soul prompt for monsoon" in system_content
    assert DIGEST_INSTRUCTION in system_content
    user_content = payload["messages"][1]["content"]
    assert "2026-07-08T10:00:00+02:00" in user_content
    assert "Task A" in user_content


@pytest.mark.asyncio
async def test_generate_reflect_includes_topic_and_context():
    settings = Settings(monsoon_soul_prompt="Soul prompt for monsoon")
    client = OllamaClient(settings)
    mock_response = _mock_chat_response("Reflection output.")
    mock_http = _mock_async_client(mock_response)

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        result = await client.generate_reflect(
            topic="work backlog",
            context_text="3 open tasks",
            now_iso="2026-07-08T10:00:00+02:00",
        )

    assert result == "Reflection output."
    user_content = mock_http.post.call_args.kwargs["json"]["messages"][1]["content"]
    assert "work backlog" in user_content
    assert "3 open tasks" in user_content


@pytest.mark.asyncio
async def test_generate_text_returns_none_on_http_error():
    settings = Settings()
    client = OllamaClient(settings)

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=_mock_async_client(httpx.HTTPError("connection failed")),
    ):
        result = await client.generate_text(user_prompt="hello")

    assert result is None


@pytest.mark.asyncio
async def test_parse_capture_still_uses_parse_prompt():
    settings = Settings(monsoon_soul_prompt="Soul prompt for monsoon")
    client = OllamaClient(settings)
    mock_response = _mock_chat_response(
        '{"kind":"todo","title":"buy milk","notes":null,'
        '"task_number":null,"due_at":null,"remind_at":null,'
        '"status":"inbox","priority":null}'
    )
    mock_http = _mock_async_client(mock_response)

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        parsed = await client.parse_capture("todo buy milk", "2026-07-08T10:00:00+02:00")

    assert parsed is not None
    assert parsed.kind == "todo"
    assert parsed.title == "buy milk"
    payload = mock_http.post.call_args.kwargs["json"]
    assert payload["messages"][0]["content"] == PARSE_PROMPT
    assert payload["format"] == "json"
    assert "Soul prompt for monsoon" not in payload["messages"][0]["content"]
