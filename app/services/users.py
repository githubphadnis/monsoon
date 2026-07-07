"""User helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.services.sender_identity import is_allowed_sender, phone_from_chat_id, resolve_sender_phone

__all__ = [
    "get_or_create_user",
    "is_allowed_sender",
    "phone_from_chat_id",
    "resolve_sender_phone",
]


def get_or_create_user(db: Session, phone: str, settings: Settings) -> User:
    user = db.scalar(select(User).where(User.phone_number == phone))
    if user:
        return user
    user = User(phone_number=phone, timezone=settings.app_timezone)
    db.add(user)
    db.flush()
    return user
