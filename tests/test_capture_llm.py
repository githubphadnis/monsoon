"""Tests for LLM-powered capture (digest, reflect)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.config import Settings
from app.models import Task, User
from app.schemas.capture import ParsedCapture
from app.services.capture_service import CaptureService
from app.services.parser import parse_with_regex

CHAT = "918291882204@c.us"


def test_reflect_parses_topic():
    settings = Settings()
    parsed = parse_with_regex("reflect griham deploy", settings)
    assert parsed is not None
    assert parsed.kind == "reflect"
    assert parsed.reflect_topic == "griham deploy"


def test_note_on_task_parses():
    settings = Settings()
    parsed = parse_with_regex("note 18 waiting for callback", settings)
    assert parsed is not None
    assert parsed.kind == "task_note"
    assert parsed.task_number == 18
    assert parsed.title == "waiting for callback"


def test_todo_with_colon_parses():
    settings = Settings()
    parsed = parse_with_regex("Todo: Make a list of all the books to read", settings)
    assert parsed is not None
    assert parsed.kind == "todo"
    assert "books" in (parsed.title or "").lower()


def _user() -> User:
    return User(id=uuid4(), phone_number="31612345678", timezone="Europe/Amsterdam")


@pytest.mark.asyncio
async def test_digest_uses_llm_when_available():
    settings = Settings(app_timezone="Europe/Amsterdam")
    service = CaptureService(MagicMock(), settings)

    with (
        patch.object(
            service,
            "_digest_context_bundle",
            return_value="## Open tasks (PRIMARY)\n#1 Call bank",
        ),
        patch.object(
            service._ollama,
            "generate_digest",
            new=AsyncMock(return_value="Today: call bank. Next: send docs."),
        ),
    ):
        result = await service._digest(_user(), chat_id=CHAT)

    assert result == "Today: call bank. Next: send docs."


@pytest.mark.asyncio
async def test_digest_falls_back_to_sql_list():
    settings = Settings(app_timezone="Europe/Amsterdam")
    db = MagicMock()
    service = CaptureService(db, settings)
    user = _user()

    with (
        patch.object(service, "_digest_context_bundle", return_value="ctx"),
        patch.object(service._ollama, "generate_digest", new=AsyncMock(return_value=None)),
        patch.object(service, "_sql_digest", return_value="*Today — open tasks*\n• Buy milk"),
    ):
        result = await service._digest(user, chat_id=CHAT)

    assert "open tasks" in result
    assert "Buy milk" in result


@pytest.mark.asyncio
async def test_reflect_dispatches_to_ollama():
    settings = Settings(app_timezone="Europe/Amsterdam")
    service = CaptureService(MagicMock(), settings)

    with (
        patch.object(service, "_context_bundle", return_value="3 open tasks"),
        patch.object(
            service._ollama,
            "generate_reflect",
            new=AsyncMock(return_value="Active: griham deploy. Next: redeploy."),
        ),
    ):
        result = await service._reflect(_user(), "griham", chat_id=CHAT)

    assert "griham deploy" in result


@pytest.mark.asyncio
async def test_dispatch_reflect_kind():
    settings = Settings()
    service = CaptureService(MagicMock(), settings)
    user = _user()
    parsed = ParsedCapture(kind="reflect", reflect_topic="health")

    with patch.object(
        service,
        "_reflect",
        new=AsyncMock(return_value="Reflection text"),
    ) as mock_reflect:
        reply = await service._dispatch(user, parsed, "msg-1", chat_id=CHAT)

    mock_reflect.assert_awaited_once_with(user, "health", chat_id=CHAT)
    assert reply == "Reflection text"


@pytest.mark.asyncio
async def test_ask_uses_ollama_with_context():
    settings = Settings(app_timezone="Europe/Amsterdam")
    service = CaptureService(MagicMock(), settings)

    with (
        patch.object(service, "_context_bundle", return_value="## Tasks\nCall Hatim"),
        patch.object(
            service._ollama,
            "generate_ask",
            new=AsyncMock(return_value="Hatim is due a call before 10:00 IST."),
        ),
    ):
        result = await service._ask(_user(), "what about hatim?", chat_id=CHAT)

    assert "Hatim" in result


@pytest.mark.asyncio
async def test_dispatch_ask_kind():
    settings = Settings()
    service = CaptureService(MagicMock(), settings)
    user = _user()
    parsed = ParsedCapture(kind="ask", title="elaborate on berberich")

    with patch.object(
        service,
        "_ask",
        new=AsyncMock(return_value="Assistant answer"),
    ) as mock_ask:
        reply = await service._dispatch(user, parsed, "msg-ask", chat_id=CHAT)

    mock_ask.assert_awaited_once_with(user, "elaborate on berberich", chat_id=CHAT)
    assert reply == "Assistant answer"


def test_personal_digest_bundle_excludes_email_wa():
    settings = Settings()
    service = CaptureService(MagicMock(), settings)
    from app.schemas.context import ContextSlice

    fake = ContextSlice(
        tasks_text="make a list of books [inbox] ref:T1",
        task_context_text="",
        emails_text="CAM invoice July",
        wa_messages_text="Finish Griham website",
        entities_text="phone:9930360555",
        topic=None,
        char_count=40,
    )
    with patch(
        "app.services.capture_service.build_context_slice",
        return_value=fake,
    ):
        bundle = service._digest_context_bundle(_user(), chat_id=CHAT)

    assert "books" in bundle
    assert "Griham" not in bundle
    assert "CAM invoice" not in bundle
    assert "9930360555" not in bundle


def test_list_skips_url_only_titles():
    settings = Settings(app_timezone="Europe/Amsterdam")
    db = MagicMock()
    service = CaptureService(db, settings)
    user = _user()

    url_task = Task(
        id=uuid4(),
        user_id=user.id,
        display_number=86,
        title="https://www.msn.com/en-in/lifestyle/foo",
        status="inbox",
    )
    real_task = Task(
        id=uuid4(),
        user_id=user.id,
        display_number=90,
        title="buy pc for P3",
        status="inbox",
    )
    db.scalars.return_value = [url_task, real_task]

    result = service._list_tasks(user, "today", chat_id=CHAT)
    assert "#90 buy pc for P3" in result
    assert "msn.com" not in result
    assert "#86" not in result


def test_question_parses_as_ask():
    from app.services.parser import looks_like_question, parse_with_regex

    assert looks_like_question("elaborate on what berberich is saying please")
    assert looks_like_question("ok what about now?")
    assert not looks_like_question("todo buy milk")
    assert parse_with_regex("todo buy milk", Settings()) is not None
