"""Tests for context slice builder."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import JSON, Uuid, create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import Base
from app.models import (
    ExtractedEntity,
    EmailMessage,
    EmailThread,
    Task,
    TaskContextItem,
    User,
    WaChat,
    WaMessage,
)
from app.models import tables as _tables  # noqa: F401
from app.schemas.context import ContextSliceRequest
from app.services.context_slice import build_context_slice


def _sqlite_engine():
    engine = create_engine("sqlite:///:memory:")
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, UUID):
                column.type = Uuid(as_uuid=True)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db() -> Session:
    engine = _sqlite_engine()
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def settings() -> Settings:
    return Settings(app_timezone="Europe/Amsterdam", waha_session="test-session")


@pytest.fixture
def user(db: Session) -> User:
    user = User(phone_number="918291882204", timezone="Europe/Amsterdam")
    db.add(user)
    db.commit()
    return user


def test_empty_db_returns_empty_sections(db: Session, settings: Settings, user: User):
    request = ContextSliceRequest(user_id=user.id)
    result = build_context_slice(db, settings, request)

    assert result.tasks_text == ""
    assert result.task_context_text == ""
    assert result.emails_text == ""
    assert result.wa_messages_text == ""
    assert result.entities_text == ""
    assert result.topic is None
    assert result.char_count == 0


def test_open_tasks_appear_in_output(db: Session, settings: Settings, user: User):
    db.add(
        Task(
            user_id=user.id,
            display_number=3,
            title="call bank",
            status="inbox",
            notes="urgent",
        )
    )
    db.add(
        Task(
            user_id=user.id,
            display_number=1,
            title="done task",
            status="done",
        )
    )
    db.commit()

    result = build_context_slice(
        db, settings, ContextSliceRequest(user_id=user.id)
    )

    assert "call bank [inbox]" in result.tasks_text
    assert "ref:T3" in result.tasks_text
    assert "notes:urgent" in result.tasks_text
    assert "done task" not in result.tasks_text
    assert result.char_count > 0


def test_topic_filter_scopes_tasks(db: Session, settings: Settings, user: User):
    """reflect <topic> must not dump unrelated open tasks into the LLM context."""
    db.add(
        Task(
            user_id=user.id,
            display_number=10,
            title="buy SD card for dashcam",
            status="today",
            due_at=None,
        )
    )
    db.add(
        Task(
            user_id=user.id,
            display_number=11,
            title="buy notebooks for school",
            status="inbox",
        )
    )
    db.add(
        Task(
            user_id=user.id,
            display_number=12,
            title="infra plan for tools / server capacity",
            status="inbox",
        )
    )
    db.commit()

    filtered = build_context_slice(
        db,
        settings,
        ContextSliceRequest(user_id=user.id, topic="dashcam"),
    )
    assert "dashcam" in filtered.tasks_text.lower()
    assert "notebooks" not in filtered.tasks_text.lower()
    assert "infra" not in filtered.tasks_text.lower()
    assert "server" not in filtered.tasks_text.lower()


def test_task_context_appears_in_output(db: Session, settings: Settings, user: User):
    task = Task(
        user_id=user.id,
        display_number=4,
        title="Book hotel in White Town",
        status="today",
    )
    db.add(task)
    db.flush()
    db.add(
        TaskContextItem(
            task_id=task.id,
            source="workflowy",
            body="research: French quarter hotels near promenade",
        )
    )
    db.commit()

    result = build_context_slice(db, settings, ContextSliceRequest(user_id=user.id))

    assert "[Book hotel in White Town]" in result.task_context_text
    assert "French quarter hotels" in result.task_context_text


def test_topic_filter_reduces_wa_lines(db: Session, settings: Settings, user: User):
    chat_a = WaChat(session="test-session", chat_id="a@c.us", name="Griham team")
    chat_b = WaChat(session="test-session", chat_id="b@c.us", name="Family")
    db.add_all([chat_a, chat_b])
    db.flush()

    ts = datetime(2025, 6, 1, 10, 0, tzinfo=UTC)
    db.add_all(
        [
            WaMessage(
                session="test-session",
                chat_uuid=chat_a.id,
                chat_id=chat_a.chat_id,
                waha_message_id="msg-griham-1",
                body="deploy griham tonight",
                message_ts=ts,
            ),
            WaMessage(
                session="test-session",
                chat_uuid=chat_b.id,
                chat_id=chat_b.chat_id,
                waha_message_id="msg-family-1",
                body="dinner at 7",
                message_ts=ts,
            ),
        ]
    )
    db.commit()

    all_result = build_context_slice(
        db, settings, ContextSliceRequest(user_id=user.id)
    )
    filtered = build_context_slice(
        db,
        settings,
        ContextSliceRequest(user_id=user.id, topic="griham"),
    )

    assert "deploy griham tonight" in all_result.wa_messages_text
    assert "dinner at 7" in all_result.wa_messages_text
    assert "deploy griham tonight" in filtered.wa_messages_text
    assert "dinner at 7" not in filtered.wa_messages_text
    assert filtered.topic == "griham"
    assert len(filtered.wa_messages_text) < len(all_result.wa_messages_text)


def test_topic_filter_matches_chat_name(db: Session, settings: Settings, user: User):
    chat = WaChat(session="test-session", chat_id="x@c.us", name="Monsoon ops")
    db.add(chat)
    db.flush()

    db.add(
        WaMessage(
            session="test-session",
            chat_uuid=chat.id,
            chat_id=chat.chat_id,
            waha_message_id="msg-ops-1",
            body="status ok",
            message_ts=datetime(2025, 6, 2, 9, 0, tzinfo=UTC),
        )
    )
    db.commit()

    result = build_context_slice(
        db,
        settings,
        ContextSliceRequest(user_id=user.id, topic="monsoon"),
    )

    assert "status ok" in result.wa_messages_text


def test_max_chars_truncates_oldest_first(db: Session, settings: Settings, user: User):
    for n in range(1, 6):
        db.add(
            Task(
                user_id=user.id,
                display_number=n,
                title=f"task number {n} with padding text",
                status="inbox",
            )
        )
    db.commit()

    result = build_context_slice(
        db,
        settings,
        ContextSliceRequest(user_id=user.id, max_chars=80),
    )

    assert result.char_count <= 80
    assert "ref:T5" in result.tasks_text
    assert "#1" not in result.tasks_text


def test_entities_linked_when_topic_set(db: Session, settings: Settings, user: User):
    chat = WaChat(session="test-session", chat_id="a@c.us", name="Griham")
    db.add(chat)
    db.flush()

    db.add(
        WaMessage(
            session="test-session",
            chat_uuid=chat.id,
            chat_id=chat.chat_id,
            waha_message_id="msg-entity-1",
            body="email prakalp@example.com",
            message_ts=datetime(2025, 6, 3, 8, 0, tzinfo=UTC),
        )
    )
    db.flush()

    db.add(
        ExtractedEntity(
            source_type="wa_message",
            source_id="msg-entity-1",
            entity_type="email",
            value="prakalp@example.com",
        )
    )
    db.add(
        ExtractedEntity(
            source_type="wa_message",
            source_id="other-msg",
            entity_type="email",
            value="other@example.com",
        )
    )
    db.commit()

    result = build_context_slice(
        db,
        settings,
        ContextSliceRequest(user_id=user.id, topic="griham"),
    )

    assert "prakalp@example.com" in result.entities_text
    assert "other@example.com" not in result.entities_text


def test_entities_all_recent_without_topic(db: Session, settings: Settings, user: User):
    db.add(
        ExtractedEntity(
            source_type="wa_message",
            source_id="orphan",
            entity_type="url",
            value="https://example.com",
        )
    )
    db.commit()

    result = build_context_slice(
        db, settings, ContextSliceRequest(user_id=user.id)
    )

    assert "url:https://example.com" in result.entities_text


def test_other_session_wa_messages_excluded(db: Session, settings: Settings, user: User):
    chat = WaChat(session="other-session", chat_id="z@c.us", name="Other")
    db.add(chat)
    db.flush()
    db.add(
        WaMessage(
            session="other-session",
            chat_uuid=chat.id,
            chat_id=chat.chat_id,
            waha_message_id="msg-other-session",
            body="should not appear",
            message_ts=datetime(2025, 6, 4, 8, 0, tzinfo=UTC),
        )
    )
    db.commit()

    result = build_context_slice(
        db, settings, ContextSliceRequest(user_id=user.id)
    )

    assert result.wa_messages_text == ""


def test_email_topic_filter(db: Session, settings: Settings, user: User):
    thread = EmailThread(gmail_thread_id="thread-pondy", subject="Hotel Pondicherry")
    db.add(thread)
    db.flush()

    ts = datetime(2025, 7, 1, 12, 0, tzinfo=UTC)
    db.add_all(
        [
            EmailMessage(
                thread_uuid=thread.id,
                gmail_message_id="gmail-pondy-1",
                gmail_thread_id="thread-pondy",
                from_email="hotel@example.com",
                from_name="White Town Inn",
                subject="Booking confirmation Pondicherry",
                snippet="check-in Friday White Town",
                received_at=ts,
            ),
            EmailMessage(
                thread_uuid=thread.id,
                gmail_message_id="gmail-other-1",
                gmail_thread_id="thread-other",
                from_email="bank@example.com",
                subject="Statement ready",
                snippet="your monthly statement",
                received_at=ts,
            ),
        ]
    )
    db.commit()

    all_result = build_context_slice(
        db, settings, ContextSliceRequest(user_id=user.id)
    )
    filtered = build_context_slice(
        db,
        settings,
        ContextSliceRequest(user_id=user.id, topic="pondicherry"),
    )

    assert "White Town Inn" in all_result.emails_text
    assert "Statement ready" in all_result.emails_text
    assert "White Town Inn" in filtered.emails_text
    assert "Statement ready" not in filtered.emails_text


def test_email_entities_included_with_topic(db: Session, settings: Settings, user: User):
    thread = EmailThread(gmail_thread_id="thread-griham", subject="Griham deploy")
    db.add(thread)
    db.flush()

    db.add(
        EmailMessage(
            thread_uuid=thread.id,
            gmail_message_id="gmail-griham-1",
            gmail_thread_id="thread-griham",
            from_email="ops@example.com",
            subject="griham deploy tonight",
            snippet="see https://griham.dev",
            received_at=datetime(2025, 7, 2, 9, 0, tzinfo=UTC),
        )
    )
    db.flush()

    db.add(
        ExtractedEntity(
            source_type="email_message",
            source_id="gmail-griham-1",
            entity_type="url",
            value="https://griham.dev",
        )
    )
    db.add(
        ExtractedEntity(
            source_type="email_message",
            source_id="other-gmail",
            entity_type="url",
            value="https://other.example",
        )
    )
    db.commit()

    result = build_context_slice(
        db,
        settings,
        ContextSliceRequest(user_id=user.id, topic="griham"),
    )

    assert "griham deploy tonight" in result.emails_text
    assert "https://griham.dev" in result.entities_text
    assert "https://other.example" not in result.entities_text


def test_wa_session_scope_excludes_other_sessions(
    db: Session, settings: Settings, user: User
):
    mine = WaChat(session="rashmi", chat_id="a@c.us", name="Self")
    other = WaChat(session="prakalp", chat_id="b@c.us", name="Dad")
    db.add_all([mine, other])
    db.flush()
    db.add(
        WaMessage(
            session="rashmi",
            chat_uuid=mine.id,
            chat_id=mine.chat_id,
            waha_message_id="r1",
            body="dentist appointment dashcam unrelated wait dentist",
            from_me=True,
            message_ts=datetime(2025, 7, 1, 10, 0, tzinfo=UTC),
        )
    )
    db.add(
        WaMessage(
            session="prakalp",
            chat_uuid=other.id,
            chat_id=other.chat_id,
            waha_message_id="p1",
            body="dentist for rashmi secret",
            from_me=False,
            message_ts=datetime(2025, 7, 1, 11, 0, tzinfo=UTC),
        )
    )
    db.commit()

    result = build_context_slice(
        db,
        settings,
        ContextSliceRequest(
            user_id=user.id,
            topic="dentist",
            waha_session="rashmi",
            include_email=False,
            include_from_me=True,
        ),
    )
    assert "appointment" in result.wa_messages_text
    assert "secret" not in result.wa_messages_text


def test_topic_tokens_drop_ask_stopwords():
    from app.services.context_slice import topic_match_tokens

    tokens = topic_match_tokens("what about the dashcam please?")
    assert "dashcam" in tokens
    assert "about" not in tokens
    assert "what" not in tokens
