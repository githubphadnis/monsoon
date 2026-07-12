"""User helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.services.sender_identity import is_allowed_sender, phone_from_chat_id, resolve_sender_phone

__all__ = [
    "get_or_create_user",
    "resolve_user_by_alias",
    "display_label_for",
    "is_allowed_sender",
    "phone_from_chat_id",
    "resolve_sender_phone",
]


def get_or_create_user(db: Session, phone: str, settings: Settings) -> User:
    user = db.scalar(select(User).where(User.phone_number == phone))
    if user:
        _maybe_set_display_name(user, phone, settings)
        return user
    alias = settings.phone_alias_map.get(phone)
    user = User(
        phone_number=phone,
        timezone=settings.app_timezone,
        display_name=alias.title() if alias else None,
    )
    db.add(user)
    db.flush()
    return user


def resolve_user_by_alias(db: Session, alias: str, settings: Settings) -> User | None:
    """Map @prakalp / prakalp → User via MONSOON_USER_ALIASES."""
    key = (alias or "").strip().lstrip("@").lower()
    if not key:
        return None
    phone = settings.user_alias_map.get(key)
    if not phone:
        return None
    return get_or_create_user(db, phone, settings)


def display_label_for(user: User, settings: Settings) -> str:
    if user.display_name:
        return user.display_name
    alias = settings.phone_alias_map.get(user.phone_number or "")
    if alias:
        return alias
    phone = user.phone_number or "?"
    return phone[-4:] if len(phone) >= 4 else phone


def _maybe_set_display_name(user: User, phone: str, settings: Settings) -> None:
    if user.display_name:
        return
    alias = settings.phone_alias_map.get(phone)
    if alias:
        user.display_name = alias.title()
