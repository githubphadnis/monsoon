"""WAHA webhook payload schemas."""

from typing import Any

from pydantic import BaseModel, Field


class WahaMessagePayload(BaseModel):
    id: str
    timestamp: int | None = None
    from_: str = Field(alias="from")
    from_me: bool | None = Field(default=None, alias="fromMe")
    to: str | None = None
    body: str | None = None
    has_media: bool | None = Field(default=None, alias="hasMedia")

    model_config = {"populate_by_name": True, "extra": "allow"}


class WahaWebhookEvent(BaseModel):
    event: str
    session: str
    payload: WahaMessagePayload | dict[str, Any]

    model_config = {"extra": "allow"}
