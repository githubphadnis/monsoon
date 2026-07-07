"""Settings parsing from environment."""

from app.config import Settings, get_settings


def test_gmail_sync_max_pages_empty_string_is_none(monkeypatch):
    monkeypatch.setenv("GMAIL_SYNC_MAX_PAGES", "")
    get_settings.cache_clear()
    try:
        settings = Settings()
        assert settings.gmail_sync_max_pages is None
    finally:
        get_settings.cache_clear()


def test_gmail_sync_max_pages_parses_integer(monkeypatch):
    monkeypatch.setenv("GMAIL_SYNC_MAX_PAGES", "10")
    get_settings.cache_clear()
    try:
        settings = Settings()
        assert settings.gmail_sync_max_pages == 10
    finally:
        get_settings.cache_clear()
        monkeypatch.delenv("GMAIL_SYNC_MAX_PAGES", raising=False)
