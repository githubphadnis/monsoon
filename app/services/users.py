"""User helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User


def phone_from_chat_id(chat_id: str) -> str:
    return chat_id.split("@", 1)[0]


def is_allowed_sender(phone: str, settings: Settings) -> bool:
    allowed = settings.allowed_numbers_set
    if not allowed:
        return True
    return phone in allowed


def get_or_create_user(db: Session, phone: str, settings: Settings) -> User:
    user = db.scalar(select(User).where(User.phone_number == phone))
    if user:
        return user
    user = User(phone_number=phone, timezone=settings.app_timezone)
    db.add(user)
    db.flush()
    return user
