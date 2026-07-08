"""Context slice schemas for LLM bundles."""

from uuid import UUID

from pydantic import BaseModel, Field


class ContextSliceRequest(BaseModel):
    user_id: UUID
    topic: str | None = None
    max_chars: int = 12000


class ContextSlice(BaseModel):
    tasks_text: str = ""
    task_context_text: str = ""
    emails_text: str = ""
    wa_messages_text: str = ""
    entities_text: str = ""
    topic: str | None = None
    char_count: int = Field(default=0, ge=0)
