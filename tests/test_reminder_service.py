"""Reminder scheduler tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import JSON, Uuid, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import Base
from app.models import OutboundMessage, Task, TaskEvent, User
from app.models import tables as _tables  # noqa: F401
from app.services.reminder_service import ReminderService


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


@pytest.mark.asyncio
async def test_send_due_clears_remind_at_and_sends(db: Session):
    user = User(id=uuid4(), phone_number="31612345678", timezone="Europe/Amsterdam")
    task = Task(
        id=uuid4(),
        user_id=user.id,
        display_number=7,
        title="Call Hatim before 1000 IST",
        status="today",
        remind_at=datetime.now(UTC) - timedelta(minutes=5),
        source="whatsapp",
    )
    db.add_all([user, task])
    db.commit()

    settings = Settings(app_timezone="Europe/Amsterdam")
    service = ReminderService(db, settings)
    service._waha = AsyncMock()
    service._waha.send_text = AsyncMock(return_value={"id": "wa-msg-1"})

    stats = await service.send_due()

    assert stats.due_found == 1
    assert stats.sent == 1
    assert stats.failed == 0
    db.refresh(task)
    assert task.remind_at is None

    outbound = db.scalar(select(OutboundMessage))
    assert outbound is not None
    assert outbound.status == "sent"
    assert "Call Hatim" in outbound.message_body
    service._waha.send_text.assert_awaited_once()

    event = db.scalar(select(TaskEvent).where(TaskEvent.event_type == "reminder_sent"))
    assert event is not None


@pytest.mark.asyncio
async def test_future_reminders_not_sent(db: Session):
    user = User(id=uuid4(), phone_number="31612345678", timezone="Europe/Amsterdam")
    task = Task(
        id=uuid4(),
        user_id=user.id,
        display_number=8,
        title="Future thing",
        status="inbox",
        remind_at=datetime.now(UTC) + timedelta(hours=2),
        source="whatsapp",
    )
    db.add_all([user, task])
    db.commit()

    service = ReminderService(db, Settings())
    service._waha = AsyncMock()
    service._waha.send_text = AsyncMock(return_value={"id": "x"})

    stats = await service.send_due()

    assert stats.due_found == 0
    assert stats.sent == 0
    service._waha.send_text.assert_not_awaited()
    db.refresh(task)
    assert task.remind_at is not None


@pytest.mark.asyncio
async def test_failed_send_keeps_remind_at_for_retry(db: Session):
    user = User(id=uuid4(), phone_number="31612345678", timezone="Europe/Amsterdam")
    past = datetime.now(UTC) - timedelta(minutes=1)
    task = Task(
        id=uuid4(),
        user_id=user.id,
        display_number=9,
        title="Retry me",
        status="inbox",
        remind_at=past,
        source="whatsapp",
    )
    db.add_all([user, task])
    db.commit()

    service = ReminderService(db, Settings())
    service._waha = AsyncMock()
    service._waha.send_text = AsyncMock(side_effect=RuntimeError("waha down"))

    stats = await service.send_due()

    assert stats.sent == 0
    assert stats.failed == 1
    db.refresh(task)
    assert task.remind_at is not None
