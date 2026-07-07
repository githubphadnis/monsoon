"""Unit tests for command parser."""

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


def test_done_command():
    settings = Settings()
    parsed = parse_with_regex("done 7", settings)
    assert parsed is not None
    assert parsed.kind == "done"
    assert parsed.task_number == 7


def test_help_command():
    settings = Settings()
    parsed = parse_with_regex("help", settings)
    assert parsed is not None
    assert parsed.kind == "help"
