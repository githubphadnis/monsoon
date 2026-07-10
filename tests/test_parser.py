"""Unit tests for command parser."""

import pytest

from app.config import Settings
from app.services.parser import parse_with_regex


def test_todo_with_tomorrow_time():
    settings = Settings(app_timezone="Europe/Amsterdam")
    parsed = parse_with_regex("todo call bank tomorrow 10am", settings)
    assert parsed is not None
    assert parsed.kind == "todo"
    assert "call bank" in (parsed.title or "")
    assert parsed.due_at is not None
    assert parsed.status == "scheduled"


def test_to_do_with_space():
    settings = Settings()
    parsed = parse_with_regex("to do buy milk", settings)
    assert parsed is not None
    assert parsed.kind == "todo"
    assert parsed.title == "buy milk"


def test_to_do_hyphenated():
    settings = Settings()
    parsed = parse_with_regex("to-do pick up parcel", settings)
    assert parsed is not None
    assert parsed.kind == "todo"
    assert parsed.title == "pick up parcel"


def test_remind_me_to():
    settings = Settings()
    parsed = parse_with_regex("remind me to call dentist tomorrow", settings)
    assert parsed is not None
    assert parsed.kind == "todo"
    assert "call dentist" in (parsed.title or "")


def test_remember_to():
    settings = Settings()
    parsed = parse_with_regex("remember to buy flowers", settings)
    assert parsed is not None
    assert parsed.kind == "todo"
    assert parsed.title == "buy flowers"


def test_done_command():
    settings = Settings()
    parsed = parse_with_regex("done 7", settings)
    assert parsed is not None
    assert parsed.kind == "done"
    assert parsed.task_number == 7


def test_complete_command():
    settings = Settings()
    parsed = parse_with_regex("complete 7", settings)
    assert parsed is not None
    assert parsed.kind == "done"
    assert parsed.task_number == 7


def test_mark_done_command():
    settings = Settings()
    parsed = parse_with_regex("mark 7 done", settings)
    assert parsed is not None
    assert parsed.kind == "done"
    assert parsed.task_number == 7


def test_list_show_tasks_aliases():
    settings = Settings()
    for cmd in ("list today", "show today", "tasks today", "list", "tasks"):
        parsed = parse_with_regex(cmd, settings)
        assert parsed is not None, cmd
        assert parsed.kind == "list"
        assert parsed.status == "today"


def test_digest_and_summary():
    settings = Settings()
    for cmd in ("digest", "digest now", "summary"):
        parsed = parse_with_regex(cmd, settings)
        assert parsed is not None, cmd
        assert parsed.kind == "digest"


def test_help_aliases():
    settings = Settings()
    for cmd in ("help", "?", "commands"):
        parsed = parse_with_regex(cmd, settings)
        assert parsed is not None, cmd
        assert parsed.kind == "help"


@pytest.mark.asyncio
async def test_free_text_question_becomes_ask():
    from unittest.mock import AsyncMock, patch

    from app.services.parser import parse_capture

    settings = Settings()
    with patch(
        "app.services.parser.OllamaClient.parse_capture",
        new=AsyncMock(return_value=None),
    ):
        parsed = await parse_capture("elaborate on what berberich is saying please", settings)

    assert parsed.kind == "ask"
    assert "berberich" in (parsed.title or "").lower()


@pytest.mark.asyncio
async def test_unknown_ollama_becomes_ask_not_todo():
    from unittest.mock import AsyncMock, patch

    from app.schemas.capture import ParsedCapture
    from app.services.parser import parse_capture

    settings = Settings()
    with patch(
        "app.services.parser.OllamaClient.parse_capture",
        new=AsyncMock(return_value=ParsedCapture(kind="unknown")),
    ):
        parsed = await parse_capture("ok what about now", settings)

    assert parsed.kind == "ask"

