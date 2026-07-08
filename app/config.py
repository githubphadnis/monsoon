"""Application configuration from environment."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_host: str = "0.0.0.0"
    app_port: int = 8080
    app_log_level: str = "INFO"
    app_timezone: str = "Europe/Amsterdam"

    database_url: str = "postgresql://monsoon:monsoon@postgres:5432/monsoon"

    workflowy_api_key: str = ""
    workflowy_root_node_id: str = ""
    workflowy_enabled: bool = True

    waha_base_url: str = "http://127.0.0.1:3000"
    waha_api_key: str = ""
    waha_session: str = "default"
    waha_webhook_path: str = "/api/webhooks/waha"

    monsoon_auto_webhook: bool = True
    monsoon_webhook_target_url: str = "http://127.0.0.1:8080/api/webhooks/waha"

    allowed_whatsapp_numbers: str = ""
    monsoon_allow_self_chat: bool = True

    ollama_base_url: str = "http://lenai:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: int = 60
    monsoon_soul_prompt: str = (
        "You are monsoon, Prakalp's personal capture assistant on WhatsApp. "
        "Be concrete, action-first, and brief. No corporate filler, no thank-yous, "
        "no 'let me know if you need help'."
    )

    monsoon_wa_backfill_chat_page_size: int = 50
    monsoon_wa_backfill_message_page_size: int = 100
    monsoon_wa_backfill_request_delay_ms: int = 250
    monsoon_wa_backfill_extract_entities: bool = True

    waha_noweb_store_enabled: bool = True
    waha_noweb_store_full_sync: bool = False

    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_user_id: str = "me"
    gmail_sync_label: str = ""  # empty = all mail; or INBOX, etc.
    gmail_sync_page_size: int = 50
    gmail_sync_max_pages: int | None = None  # pilot cap; None = no limit
    monsoon_scheduler_enabled: bool = True
    # Same-day catch-up defaults: small batches, frequent loops (safe on notcoolio).
    monsoon_gmail_sync_interval_minutes: int = 5
    monsoon_gmail_sync_batch_pages: int = 5
    monsoon_wa_sync_interval_minutes: int = 5
    monsoon_wa_sync_batch_chats: int = 5
    monsoon_workflowy_sync_interval_minutes: int = 20
    monsoon_reminder_interval_minutes: int = 1
    gmail_include_spam_trash: bool = False  # set true to also index Spam/Trash

    @field_validator("gmail_sync_max_pages", mode="before")
    @classmethod
    def _empty_optional_int(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @property
    def allowed_numbers_set(self) -> set[str]:
        return {n.strip() for n in self.allowed_whatsapp_numbers.split(",") if n.strip()}

    @property
    def gmail_configured(self) -> bool:
        return bool(self.gmail_client_id and self.gmail_client_secret and self.gmail_refresh_token)

    @property
    def workflowy_configured(self) -> bool:
        return bool(self.workflowy_api_key)

    @property
    def workflowy_active(self) -> bool:
        return self.workflowy_enabled and self.workflowy_configured


@lru_cache
def get_settings() -> Settings:
    return Settings()
