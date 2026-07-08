"""Tests for LLM-powered capture (digest, reflect)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.config import Settings
from app.models import User
from app.schemas.capture import ParsedCapture
from app.services.capture_service import CaptureService
from app.services.parser import parse_with_regex


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


def _user() -> User:
    return User(id=uuid4(), phone_number="31612345678", timezone="Europe/Amsterdam")


@pytest.mark.asyncio
async def test_digest_uses_llm_when_available():
    settings = Settings(app_timezone="Europe/Amsterdam")
    service = CaptureService(MagicMock(), settings)

    with (
        patch.object(service, "_context_bundle", return_value="## Tasks\n#1 Call bank"),
        patch.object(
            service._ollama,
            "generate_digest",
            new=AsyncMock(return_value="Today: call bank. Next: send docs."),
        ),
    ):
        result = await service._digest(_user())

    assert result == "Today: call bank. Next: send docs."


@pytest.mark.asyncio
async def test_digest_falls_back_to_sql_list():
    settings = Settings(app_timezone="Europe/Amsterdam")
    db = MagicMock()
    service = CaptureService(db, settings)
    user = _user()

    with (
        patch.object(service, "_context_bundle", return_value="ctx"),
        patch.object(service._ollama, "generate_digest", new=AsyncMock(return_value=None)),
        patch.object(service, "_sql_digest", return_value="*Digest*\n#2 Buy milk [today]"),
    ):
        result = await service._digest(user)

    assert "*Digest*" in result
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
        result = await service._reflect(_user(), "griham")

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
        reply = await service._dispatch(user, parsed, "msg-1")

    mock_reflect.assert_awaited_once_with(user, "health")
    assert reply == "Reflection text"
