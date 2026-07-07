"""Application configuration from environment."""

from functools import lru_cache

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

    waha_base_url: str = "http://waha:3000"
    waha_api_key: str = ""
    waha_session: str = "default"
    waha_webhook_path: str = "/api/webhooks/waha"

    allowed_whatsapp_numbers: str = ""
    monsoon_allow_self_chat: bool = True

    ollama_base_url: str = "http://lenai:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: int = 60
    monsoon_soul_prompt: str = (
        "You are monsoon, a concise personal assistant. Be practical, proactive, and brief."
    )

    @property
    def allowed_numbers_set(self) -> set[str]:
        return {n.strip() for n in self.allowed_whatsapp_numbers.split(",") if n.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
