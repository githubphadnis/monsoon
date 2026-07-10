"""WorkFlowy mirror push tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.integrations.workflowy import WorkFlowyClient
from app.models import Task, User
from app.services.workflowy_mirror import BUCKETS, WorkFlowyMirrorService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        workflowy_api_key="test-wf-key",
        workflowy_root_node_id="root-node-123",
        workflowy_enabled=True,
        app_timezone="Europe/Amsterdam",
    )


@pytest.fixture
def user() -> User:
    return User(
        id=uuid.uuid4(),
        phone_number="+31600000000",
        timezone="Europe/Amsterdam",
        workflowy_root_node_id="root-node-123",
    )


@pytest.fixture
def task(user: User) -> Task:
    return Task(
        id=uuid.uuid4(),
        user_id=user.id,
        display_number=18,
        title="Call bank about wire transfer",
        status="waiting",
        source="whatsapp",
        due_at=datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc),
    )


def _mock_db(user: User) -> MagicMock:
    db = MagicMock()
    db.get.side_effect = lambda model, pk: user if model is User and pk == user.id else None
    db.scalar.return_value = None
    return db


@pytest.mark.asyncio
async def test_push_task_created_puts_metadata_in_note(settings: Settings, user: User, task: Task):
    db = _mock_db(user)
    service = WorkFlowyMirrorService(db, settings)

    bucket_nodes = {key: f"bucket-{key}" for key in BUCKETS}
    create_calls: list[dict] = []

    async def fake_create_node(parent_id, name, *, layout_mode=None, note=None, position="bottom"):
        create_calls.append(
            {
                "parent_id": parent_id,
                "name": name,
                "layout_mode": layout_mode,
                "note": note,
                "position": position,
            }
        )
        if layout_mode == "todo":
            return "task-node-abc"
        return f"child-{len(create_calls)}"

    service._client = AsyncMock(spec=WorkFlowyClient)
    service._client.configured = True
    service._client.list_nodes = AsyncMock(return_value=[])
    service._client.create_node = AsyncMock(side_effect=fake_create_node)
    service._client.create_child = AsyncMock(side_effect=fake_create_node)
    service._bucket_cache = bucket_nodes

    node_id = await service.push_task_created(task, user=user)

    assert node_id == "task-node-abc"
    assert task.workflowy_node_id == "task-node-abc"

    assert len(create_calls) == 1
    assert create_calls[0]["parent_id"] == "bucket-waiting"
    assert create_calls[0]["name"] == "Call bank about wire transfer"
    assert create_calls[0]["layout_mode"] == "todo"
    assert create_calls[0]["note"] == "T18 · whatsapp · waiting · due 2026-07-08 12:00"
    service._client.create_child.assert_not_called()


@pytest.mark.asyncio
async def test_push_task_created_skips_without_api_key(settings: Settings, user: User, task: Task):
    settings_no_key = Settings(workflowy_api_key="", workflowy_enabled=True)
    db = _mock_db(user)
    service = WorkFlowyMirrorService(db, settings_no_key)

    node_id = await service.push_task_created(task, user=user)

    assert node_id is None
    assert task.workflowy_node_id is None


@pytest.mark.asyncio
async def test_push_context_item_creates_child_and_db_row(settings: Settings, user: User, task: Task):
    task.workflowy_node_id = "task-node-abc"
    db = _mock_db(user)
    service = WorkFlowyMirrorService(db, settings)

    service._client = AsyncMock(spec=WorkFlowyClient)
    service._client.configured = True
    service._client.create_child = AsyncMock(return_value="context-node-xyz")

    item = await service.push_context_item(
        task,
        "spoke to agent, case #44921",
        "whatsapp",
        source_ref="msg-123",
    )

    assert item is not None
    assert item.body == "spoke to agent, case #44921"
    assert item.source == "whatsapp"
    assert item.source_ref == "msg-123"
    assert item.workflowy_node_id == "context-node-xyz"
    service._client.create_child.assert_awaited_once_with(
        "task-node-abc",
        "spoke to agent, case #44921",
        position="bottom",
    )
    db.add.assert_called()
    db.flush.assert_called()
