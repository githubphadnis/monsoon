"""Gmail sync list/history resume behavior."""

from unittest.mock import MagicMock

from app.config import Settings
from app.services.gmail_sync import HISTORY_KEY, PAGE_TOKEN_KEY, GmailSyncService


def test_run_prefers_incomplete_list_over_history():
    settings = Settings(
        gmail_client_id="c",
        gmail_client_secret="s",
        gmail_refresh_token="t",
    )
    db = MagicMock()
    service = GmailSyncService.__new__(GmailSyncService)
    service._db = db
    service._settings = settings
    service._service = MagicMock()

    cursors = {PAGE_TOKEN_KEY: "page-token", HISTORY_KEY: "9781885"}

    def get_sync(key: str):
        return cursors.get(key)

    def set_sync(key: str, value: str | None):
        if value is None:
            cursors.pop(key, None)
        else:
            cursors[key] = value

    service._get_sync_value = get_sync  # type: ignore[method-assign]
    service._set_sync_value = set_sync  # type: ignore[method-assign]
    service._sync_list = MagicMock()  # type: ignore[method-assign]
    service._sync_history = MagicMock()  # type: ignore[method-assign]

    # Simulate list still in progress — complete by clearing page token mid-run.
    def fake_list(stats, *, max_pages=None):
        cursors.pop(PAGE_TOKEN_KEY, None)

    service._sync_list.side_effect = fake_list
    service._service.users.return_value.getProfile.return_value.execute.return_value = {
        "historyId": "999"
    }

    service.run(full=False, max_pages=2)

    service._sync_list.assert_called_once()
    service._sync_history.assert_not_called()
    assert cursors[HISTORY_KEY] == "999"


def test_run_uses_history_when_list_complete():
    settings = Settings(
        gmail_client_id="c",
        gmail_client_secret="s",
        gmail_refresh_token="t",
    )
    service = GmailSyncService.__new__(GmailSyncService)
    service._db = MagicMock()
    service._settings = settings
    service._service = MagicMock()

    cursors = {HISTORY_KEY: "9781885"}

    service._get_sync_value = lambda key: cursors.get(key)  # type: ignore[method-assign]
    service._set_sync_value = lambda key, value: cursors.__setitem__(key, value)  # type: ignore[method-assign]
    service._sync_list = MagicMock()  # type: ignore[method-assign]
    service._sync_history = MagicMock()  # type: ignore[method-assign]
    service._service.users.return_value.getProfile.return_value.execute.return_value = {
        "historyId": "9781886"
    }

    service.run(full=False)

    service._sync_history.assert_called_once()
    service._sync_list.assert_not_called()
