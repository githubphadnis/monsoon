"""WAHA webhook routes."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas.waha import WahaMessagePayload, WahaWebhookEvent
from app.services.capture_service import CaptureService
from app.services.sender_identity import resolve_reply_chat_id, resolve_sender_phone

logger = logging.getLogger("monsoon.api.webhooks")

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _verify_webhook_key(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> None:
    if not settings.waha_api_key:
        return
    if x_api_key != settings.waha_api_key:
        logger.warning("Webhook rejected: missing or invalid X-Api-Key")
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
    logger.info(
        "Webhook received event=%s session=%s",
        event.event,
        event.session,
    )

    if event.event not in {"message", "message.any"}:
        return {"status": "ignored", "reason": "event"}

    if isinstance(event.payload, dict):
        payload = WahaMessagePayload.model_validate(event.payload)
    else:
        payload = event.payload

    if payload.from_me and not settings.monsoon_allow_self_chat:
        return {"status": "ignored", "reason": "from_me"}

    if payload.has_media and not (payload.body or "").strip():
        return {"status": "ignored", "reason": "media_only"}

    text = (payload.body or "").strip()
    if not text:
        return {"status": "ignored", "reason": "empty"}

    sender = payload.from_
    payload_extra = payload.model_dump() if hasattr(payload, "model_dump") else {}
    phone = resolve_sender_phone(
        from_id=sender,
        from_me=payload.from_me,
        body=body,
        payload_extra=payload_extra,
        settings=settings,
    )
    if not phone:
        logger.warning("Rejected sender %s (from_me=%s)", sender, payload.from_me)
        raise HTTPException(status_code=403, detail="Sender not allowed")

    me = body.get("me") if isinstance(body.get("me"), dict) else {}
    me_id = str(me.get("id", "")) or None
    chat_id = resolve_reply_chat_id(sender, payload_extra, me_id=me_id)
    logger.info("Processing capture from=%s chat_id=%s phone=%s", sender, chat_id, phone)
    service = CaptureService(db, settings)
    try:
        reply = await service.handle_text(
            source_message_id=payload.id,
            chat_id=chat_id,
            sender_phone=phone,
            text=text,
            raw_payload=body,
        )
        logger.info("Webhook processed reply_sent=%s", bool(reply))
    except Exception:
        logger.exception("Webhook processing failed")
        return {"status": "error"}
    return {"status": "ok"}
