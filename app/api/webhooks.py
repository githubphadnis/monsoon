"""WAHA webhook routes."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas.waha import WahaMessagePayload, WahaWebhookEvent
from app.services.capture_service import CaptureService
from app.services.outbound_guard import is_outbound_echo
from app.services.sender_identity import (
    is_chat_allowed,
    is_self_chat,
    resolve_conversation_chat_id,
    resolve_sender_phone,
)

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

    if payload.has_media and not (payload.body or "").strip():
        return {"status": "ignored", "reason": "media_only"}

    text = (payload.body or "").strip()
    if not text:
        return {"status": "ignored", "reason": "empty"}

    if is_outbound_echo(db, message_id=payload.id, text=text):
        logger.info("Ignored bot echo message_id=%s", payload.id)
        return {"status": "ignored", "reason": "bot_echo"}

    sender = payload.from_
    payload_extra = payload.model_dump() if hasattr(payload, "model_dump") else {}

    me = body.get("me") if isinstance(body.get("me"), dict) else {}
    me_id = str(me.get("id", "")) or None
    chat_id = resolve_conversation_chat_id(
        sender,
        payload_extra,
        from_me=payload.from_me,
        to_id=payload.to,
        me_id=me_id,
    )

    # fromMe: only Message-yourself is a monsoon command surface.
    # Outbound into a peer chat (e.g. dad typing in son's 1:1) must not trigger the bot.
    if payload.from_me:
        if not settings.monsoon_allow_self_chat:
            return {"status": "ignored", "reason": "from_me"}
        if not is_self_chat(chat_id, me_id):
            logger.info(
                "Ignored from_me in peer chat chat_id=%s me=%s",
                chat_id,
                me_id,
            )
            return {"status": "ignored", "reason": "from_me_peer"}

    # Chat-id gate first — never reply based on sender alone.
    if not is_chat_allowed(chat_id, settings):
        logger.info(
            "Ignored chat outside allowlist chat_id=%s from=%s from_me=%s to=%s allowed=%s",
            chat_id,
            sender,
            payload.from_me,
            payload.to,
            sorted(settings.allowed_chat_ids_set) or ["<empty-deny-all>"],
        )
        return {"status": "ignored", "reason": "chat_not_allowed"}

    phone = resolve_sender_phone(
        from_id=sender,
        from_me=payload.from_me,
        body=body,
        payload_extra=payload_extra,
        settings=settings,
    )
    if not phone:
        logger.warning(
            "Rejected sender from=%s from_me=%s chat_id=%s (check ALLOWED_WHATSAPP_NUMBERS + LID alt)",
            sender,
            payload.from_me,
            chat_id,
        )
        raise HTTPException(status_code=403, detail="Sender not allowed")

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
