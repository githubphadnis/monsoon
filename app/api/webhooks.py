"""WAHA webhook routes."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas.waha import WahaMessagePayload, WahaWebhookEvent
from app.services.capture_service import CaptureService
from app.services.users import is_allowed_sender, phone_from_chat_id

logger = logging.getLogger("monsoon.api.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _verify_webhook_key(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> None:
    if not settings.waha_api_key:
        return
    if x_api_key != settings.waha_api_key:
        raise HTTPException(status_code=401, detail="Invalid webhook API key")


@router.post("/waha")
async def waha_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(_verify_webhook_key),
) -> dict[str, str]:
    body = await request.json()
    event = WahaWebhookEvent.model_validate(body)

    if event.event not in {"message", "message.any"}:
        return {"status": "ignored", "reason": "event"}

    if isinstance(event.payload, dict):
        payload = WahaMessagePayload.model_validate(event.payload)
    else:
        payload = event.payload

    if payload.from_me:
        return {"status": "ignored", "reason": "from_me"}

    if payload.has_media and not (payload.body or "").strip():
        return {"status": "ignored", "reason": "media_only"}

    text = (payload.body or "").strip()
    if not text:
        return {"status": "ignored", "reason": "empty"}

    sender = payload.from_
    phone = phone_from_chat_id(sender)
    if not is_allowed_sender(phone, settings):
        logger.warning("Rejected sender %s", phone)
        raise HTTPException(status_code=403, detail="Sender not allowed")

    chat_id = sender

    service = CaptureService(db, settings)
    try:
        await service.handle_text(
            source_message_id=payload.id,
            chat_id=chat_id,
            sender_id=sender,
            text=text,
            raw_payload=body,
        )
    except Exception:
        logger.exception("Webhook processing failed")
        return {"status": "error"}
    return {"status": "ok"}
