"""Tests for scheduled daily digest."""

from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from app.config import Settings
from app.services.daily_digest import DailyDigestService


def test_should_send_after_target_once_per_day():
    settings = Settings(
        app_timezone="Europe/Amsterdam",
        monsoon_daily_digest_enabled=True,
        monsoon_daily_digest_hour=8,
        monsoon_daily_digest_minute=0,
    )
    db = MagicMock()
    db.get.return_value = None
    svc = DailyDigestService(db, settings)

    before = datetime(2026, 7, 16, 7, 59, tzinfo=ZoneInfo("Europe/Amsterdam"))
    assert not svc.should_send_now(before)

    after = datetime(2026, 7, 16, 8, 5, tzinfo=ZoneInfo("Europe/Amsterdam"))
    assert svc.should_send_now(after)


def test_daily_digest_recipient_defaults_to_primary_session_phones():
    s = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map=(
            "918291882204:prakalp,918291882206:Rashmi,46704098198:Prathamesh"
        ),
        monsoon_daily_digest_phones="",
    )
    assert s.daily_digest_recipient_phones() == ["918291882204"]
    assert s.digest_includes_email_for("918291882204") is False  # gmail not configured
    s2 = Settings(
        waha_session="prakalp",
        monsoon_daily_digest_phones="918291882204",
        gmail_client_id="a",
        gmail_client_secret="b",
        gmail_refresh_token="c",
    )
    assert s2.digest_includes_email_for("918291882204") is True
    assert s2.digest_includes_email_for("918291882206") is False
