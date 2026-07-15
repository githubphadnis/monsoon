"""Webhook setup — primary vs secondary session readiness."""

from unittest.mock import patch

from app.config import Settings
from app.integrations.whatsapp.webhook_setup import configure_waha_webhook


def test_configure_succeeds_when_only_primary_exists():
    settings = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map="918291882206:rashmi,46704098198:prathamesh",
        monsoon_auto_webhook=True,
        waha_api_key="secret",
    )

    def fake_status(_settings, session: str) -> dict:
        if session == "prakalp":
            return {
                "configured": False,
                "session": session,
                "session_status": "WORKING",
                "detail": None,
            }
        return {
            "configured": False,
            "session": session,
            "session_status": None,
            "detail": "session_not_found",
        }

    with (
        patch(
            "app.integrations.whatsapp.webhook_setup.get_webhook_status_for_session",
            side_effect=fake_status,
        ),
        patch(
            "app.integrations.whatsapp.webhook_setup.configure_waha_webhook_session",
            return_value=True,
        ) as configure_one,
    ):
        assert configure_waha_webhook(settings) is True
        configure_one.assert_called_once_with(settings, "prakalp")


def test_configure_fails_when_primary_missing():
    settings = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map="918291882206:rashmi",
        monsoon_auto_webhook=True,
    )

    def fake_status(_settings, session: str) -> dict:
        return {
            "configured": False,
            "session": session,
            "session_status": None,
            "detail": "session_not_found",
        }

    with patch(
        "app.integrations.whatsapp.webhook_setup.get_webhook_status_for_session",
        side_effect=fake_status,
    ):
        assert configure_waha_webhook(settings) is False


def test_webhook_match_requires_api_key_header():
    from app.integrations.whatsapp.webhook_setup import _webhook_matches

    settings = Settings(waha_api_key="secret")
    hook = {
        "url": "http://127.0.0.1:8080/api/webhooks/waha",
        "events": ["message.any"],
    }
    assert (
        _webhook_matches(
            hook, settings, target_url="http://127.0.0.1:8080/api/webhooks/waha"
        )
        is False
    )
    hook["customHeaders"] = [{"name": "X-Api-Key", "value": "secret"}]
    assert (
        _webhook_matches(
            hook, settings, target_url="http://127.0.0.1:8080/api/webhooks/waha"
        )
        is True
    )
