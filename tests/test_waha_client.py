"""WAHA client and session setup tests."""

from app.config import Settings
from app.integrations.whatsapp.waha_client import WahaClient
from app.integrations.whatsapp.webhook_setup import _build_session_config


def test_chat_list_params_use_conversation_timestamp():
    params = WahaClient.chat_list_params(limit=50, offset=0)
    assert params["sortBy"] == "conversationTimestamp"
    assert params["sortOrder"] == "desc"
    assert params["limit"] == 50
    assert "messageTimestamp" not in params.values()


def test_build_session_config_enables_noweb_store():
    settings = Settings(
        monsoon_webhook_target_url="http://127.0.0.1:8080/api/webhooks/waha",
        waha_api_key="test-key",
        waha_noweb_store_enabled=True,
        waha_noweb_store_full_sync=False,
    )
    patch = _build_session_config(settings, {"config": {"webhooks": []}})
    assert patch["config"]["webhooks"][0]["url"].endswith("/api/webhooks/waha")
    assert patch["config"]["noweb"]["store"]["enabled"] is True
    assert patch["config"]["noweb"]["store"]["fullSync"] is False
