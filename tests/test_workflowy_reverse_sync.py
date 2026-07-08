from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy import JSON, Uuid, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db import Base
from app.models import Task, TaskContextItem, User
from app.models import tables as _tables  # noqa: F401
from app.services.workflowy_mirror import WorkFlowyMirrorService


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


def test_sync_task_context_skips_system_children_and_upserts_context():
    engine = _sqlite_engine()
    db: Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

    user = User(
        id=uuid4(),
        phone_number="+31612345678",
        timezone="Europe/Amsterdam",
        workflowy_root_node_id="root-node-123",
    )
    task = Task(
        id=uuid4(),
        user_id=user.id,
        display_number=18,
        title="Call bank about wire transfer",
        status="waiting",
        source="whatsapp",
        workflowy_node_id="task-node-abc",
    )
    db.add_all([user, task])
    db.commit()

    service = WorkFlowyMirrorService(
        db,
        Settings(
            workflowy_api_key="wf-key",
            workflowy_root_node_id="root-node-123",
            workflowy_enabled=True,
        ),
    )
    service._client = AsyncMock()
    service._client.list_nodes = AsyncMock(
        return_value=[
            {"id": "sys-1", "name": "id: T18"},
            {"id": "ctx-1", "name": "waiting: callback promised Thursday"},
            {"id": "ctx-2", "name": "link: https://bank.com/status"},
        ]
    )

    import asyncio

    synced = asyncio.run(service.sync_task_context(task))
    db.commit()

    items = list(
        db.scalars(
            select(TaskContextItem).where(TaskContextItem.task_id == task.id).order_by(TaskContextItem.body)
        )
    )
    assert synced == 2
    assert [item.body for item in items] == [
        "link: https://bank.com/status",
        "waiting: callback promised Thursday",
    ]
    assert all(item.source == "workflowy" for item in items)
    assert {item.workflowy_node_id for item in items} == {"ctx-1", "ctx-2"}

    db.close()
