"""Parsed capture intent from WhatsApp text."""

from datetime import datetime

from pydantic import BaseModel, Field


class ParsedCapture(BaseModel):
    kind: str = Field(
        description=(
            "todo | note | task_note | done | list | digest | reflect | ask | help | unknown"
        )
    )
    title: str | None = None
    notes: str | None = None
    task_number: int | None = None
    reflect_topic: str | None = None
    due_at: datetime | None = None
    remind_at: datetime | None = None
    status: str | None = None
    priority: str | None = None
    raw_command: str | None = None
