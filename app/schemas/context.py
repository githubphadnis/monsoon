"""Context slice schemas for LLM bundles."""

from uuid import UUID

from pydantic import BaseModel, Field


class ContextSliceRequest(BaseModel):
    user_id: UUID
    topic: str | None = None
    max_chars: int = 12000
    # When set, only index WA for this WAHA session (person-scoped; no atlas leak).
    waha_session: str | None = None
    include_wa: bool = True
    include_email: bool = True
    # Personal ask/reflect: include from_me (Message yourself) but still drop bot acks.
    include_from_me: bool = False


class ContextSlice(BaseModel):
    tasks_text: str = ""
    task_context_text: str = ""
    emails_text: str = ""
    wa_messages_text: str = ""
    entities_text: str = ""
    topic: str | None = None
    char_count: int = Field(default=0, ge=0)
