"""Push-sync tasks and context to WorkFlowy."""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.workflowy import WorkFlowyClient
from app.models import SyncState, Task, TaskContextItem, User

logger = logging.getLogger("monsoon.workflowy_mirror")

BUCKETS: dict[str, str] = {
    "inbox": "Inbox",
    "today": "Today",
    "next": "Next",
    "waiting": "Waiting",
    "scheduled": "Scheduled",
    "done": "Done",
}

SYNC_STATE_KEY = "workflowy_bucket_nodes"
SYSTEM_PREFIXES = ("id:", "source:", "due:", "status:")


class WorkFlowyMirrorService:
    def __init__(self, db: Session, settings: Settings, client: WorkFlowyClient | None = None) -> None:
        self._db = db
        self._settings = settings
        self._client = client or WorkFlowyClient(settings)
        self._bucket_cache: dict[str, str] | None = None

    @property
    def active(self) -> bool:
        return self._settings.workflowy_active

    def _root_node_id(self, user: User) -> str | None:
        return user.workflowy_root_node_id or self._settings.workflowy_root_node_id or None

    async def ensure_bucket_nodes(self, user: User) -> dict[str, str]:
        """Map task status keys to WorkFlowy bucket parent node ids."""
        if self._bucket_cache:
            return self._bucket_cache

        cached = self._db.get(SyncState, SYNC_STATE_KEY)
        if cached and cached.value:
            self._bucket_cache = {k: str(v) for k, v in cached.value.items()}
            return self._bucket_cache

        root_id = self._root_node_id(user)
        if not root_id:
            logger.warning("WorkFlowy mirror skipped — no root node id configured")
            return {}

        if not self.active:
            return {}

        children = await self._client.list_nodes(root_id)
        by_name = {node.get("name"): str(node["id"]) for node in children if node.get("id") and node.get("name")}

        bucket_ids: dict[str, str] = {}
        for status_key, bucket_name in BUCKETS.items():
            node_id = by_name.get(bucket_name)
            if not node_id:
                node_id = await self._client.create_child(root_id, bucket_name)
            if node_id:
                bucket_ids[status_key] = node_id

        if bucket_ids:
            if cached:
                cached.value = bucket_ids
            else:
                self._db.add(SyncState(key=SYNC_STATE_KEY, value=bucket_ids))
            self._db.flush()
            self._bucket_cache = bucket_ids

        return bucket_ids

    def _format_due(self, due_at: datetime | None) -> str | None:
        if not due_at:
            return None
        tz = ZoneInfo(self._settings.app_timezone)
        local = due_at.astimezone(tz) if due_at.tzinfo else due_at.replace(tzinfo=tz)
        return local.strftime("%Y-%m-%d %H:%M")

    async def push_task_created(self, task: Task, *, user: User | None = None) -> str | None:
        """Create a todo under the status bucket plus system metadata children."""
        if not self.active:
            return None

        if task.workflowy_node_id:
            return task.workflowy_node_id

        task_user = user or self._db.get(User, task.user_id)
        if not task_user:
            logger.warning("WorkFlowy push skipped — user not found for task %s", task.id)
            return None

        buckets = await self.ensure_bucket_nodes(task_user)
        parent_id = buckets.get(task.status) or buckets.get("inbox")
        if not parent_id:
            logger.warning("WorkFlowy push skipped — no bucket for status %s", task.status)
            return None

        node_id = await self._client.create_node(
            parent_id,
            task.title,
            layout_mode="todo",
            note=self._system_note(task),
            position="bottom",
        )
        if not node_id:
            return None

        task.workflowy_node_id = node_id
        self._db.flush()
        logger.info("WorkFlowy task mirrored T%s → %s", task.display_number, node_id)
        return node_id

    def _system_note(self, task: Task) -> str:
        """Compact machine metadata for the WorkFlowy note field (not child bullets)."""
        parts = [f"T{task.display_number}", task.source or "whatsapp", task.status]
        due_text = self._format_due(task.due_at)
        if due_text:
            parts.append(f"due {due_text}")
        return " · ".join(parts)

    async def push_context_item(
        self,
        task: Task,
        body: str,
        source: str,
        *,
        source_ref: str | None = None,
    ) -> TaskContextItem | None:
        """Append a context child bullet in WorkFlowy and persist TaskContextItem."""
        if not body.strip():
            return None

        item = TaskContextItem(
            task_id=task.id,
            source=source,
            body=body.strip(),
            source_ref=source_ref,
        )
        self._db.add(item)
        self._db.flush()

        if not self.active or not task.workflowy_node_id:
            return item

        node_id = await self._client.create_child(task.workflowy_node_id, body.strip(), position="bottom")
        if node_id:
            item.workflowy_node_id = node_id
            self._db.flush()

        return item

    async def complete_task(self, task: Task) -> bool:
        """Mark the WorkFlowy todo node complete when task is done."""
        if not self.active or not task.workflowy_node_id:
            return False
        return await self._client.complete_node(task.workflowy_node_id)

    async def sync_task_context(self, task: Task) -> int:
        """Pull non-system child bullets from WorkFlowy into task_context_items."""
        if not self.active or not task.workflowy_node_id:
            return 0

        nodes = await self._client.list_nodes(task.workflowy_node_id)
        synced = 0
        for node in nodes:
            node_id = str(node.get("id") or "")
            body = (node.get("name") or "").strip()
            if not node_id or not body:
                continue
            if body.lower().startswith(SYSTEM_PREFIXES):
                continue

            item = self._db.scalar(
                select(TaskContextItem).where(
                    TaskContextItem.task_id == task.id,
                    TaskContextItem.workflowy_node_id == node_id,
                )
            )
            if item:
                if item.body != body:
                    item.body = body
                synced += 1
                continue

            existing = self._db.scalar(
                select(TaskContextItem).where(
                    TaskContextItem.task_id == task.id,
                    TaskContextItem.body == body,
                )
            )
            if existing:
                if not existing.workflowy_node_id:
                    existing.workflowy_node_id = node_id
                if existing.source == "monsoon":
                    existing.source = "workflowy"
                synced += 1
                continue

            self._db.add(
                TaskContextItem(
                    task_id=task.id,
                    workflowy_node_id=node_id,
                    source="workflowy",
                    body=body,
                )
            )
            synced += 1

        self._db.flush()
        return synced

    async def sync_user_context(self, user_id) -> int:
        """Pull context children for all WorkFlowy-linked tasks for a user."""
        tasks = list(
            self._db.scalars(
                select(Task).where(
                    Task.user_id == user_id,
                    Task.workflowy_node_id.is_not(None),
                )
            )
        )
        synced = 0
        for task in tasks:
            synced += await self.sync_task_context(task)
        return synced
