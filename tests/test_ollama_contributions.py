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
    mock_response = _mock_chat_response(
        "Finish the Griham website by Saturday. Next: call bank."
    )
    mock_http = _mock_async_client(mock_response)

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        result = await client.generate_digest(
            context_text="## Open tasks (PRIMARY)\nFinish Griham website [inbox] ref:T1\nCall bank [today] ref:T2",
            now_iso="2026-07-08T10:00:00+02:00",
        )

    assert result is not None
    assert "Griham" in result
    payload = mock_http.post.call_args.kwargs["json"]
    system_content = payload["messages"][0]["content"]
    assert "Soul prompt for monsoon" in system_content
    assert DIGEST_INSTRUCTION in system_content
    assert "action digest" in system_content
    assert payload.get("options", {}).get("temperature") == 0.2
    user_content = payload["messages"][1]["content"]
    assert "2026-07-08T10:00:00+02:00" in user_content
    assert "Open tasks" in user_content


@pytest.mark.asyncio
async def test_generate_digest_rejects_entity_dump():
    from app.integrations.ollama.client import looks_like_bad_digest

    assert looks_like_bad_digest(
        "### Entities Identified:\n*Phone Numbers:*\n- 9930360555\n"
        "a@b.com c@d.com e@f.com g@h.com h@i.com"
    )
    assert looks_like_bad_digest("Thank you for sharing this information.")
    assert looks_like_bad_digest(
        "Thank you for reaching out. I'll respond to your queries in the order "
        "they were received:\n\n1. *Golf Meadows CHSL Receipts*:\n   - payments\n"
        "2. *WhatsApp Messages*:\n   - insurance\n"
        "3. *Life Insurance Update*:\n   - offer\n"
        "Feel free to let me know if you need help!"
    )
    assert not looks_like_bad_digest(
        "Finish the Griham website by Saturday. Call Hatim before 10:00 IST."
    )

    settings = Settings(monsoon_soul_prompt="Soul prompt for monsoon")
    client = OllamaClient(settings)
    dump = (
        "Thank you for reaching out. I'll respond to your queries:\n"
        "1. *Golf Meadows*:\n foo\n2. *WhatsApp*:\n bar\n3. *Insurance*:\n baz\n"
        "Feel free to let me know!"
    )
    mock_http = _mock_async_client(_mock_chat_response(dump))

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        result = await client.generate_digest(
            context_text="## Open tasks (PRIMARY)\nCall bank [inbox] ref:T1",
            now_iso="2026-07-08T10:00:00+02:00",
        )

    assert result is None


@pytest.mark.asyncio
async def test_generate_digest_rejects_when_tasks_ignored():
    settings = Settings(monsoon_soul_prompt="Soul prompt for monsoon")
    client = OllamaClient(settings)
    # Looks clean but never mentions the open task
    mock_http = _mock_async_client(
        _mock_chat_response("Society mail looks quiet today. Next: check the weather.")
    )

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        result = await client.generate_digest(
            context_text="## Open tasks (PRIMARY)\nFinish Griham website and ppt [inbox] ref:T87",
            now_iso="2026-07-08T10:00:00+02:00",
        )

    assert result is None


@pytest.mark.asyncio
async def test_generate_ask_includes_question_and_context():
    from app.integrations.ollama.client import ASK_INSTRUCTION

    settings = Settings(monsoon_soul_prompt="Soul prompt for monsoon")
    client = OllamaClient(settings)
    mock_response = _mock_chat_response("Berberich is asking about the timeline.")
    mock_http = _mock_async_client(mock_response)

    with patch(
        "app.integrations.ollama.client.httpx.AsyncClient",
        return_value=mock_http,
    ):
        result = await client.generate_ask(
            question="elaborate on what berberich is saying",
            context_text="## Email\n[Berberich] timeline update",
            now_iso="2026-07-08T10:00:00+02:00",
        )

    assert "Berberich" in (result or "")
    payload = mock_http.post.call_args.kwargs["json"]
    assert ASK_INSTRUCTION in payload["messages"][0]["content"]
    user_content = payload["messages"][1]["content"]
    assert "elaborate on what berberich is saying" in user_content
    assert "timeline update" in user_content


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
