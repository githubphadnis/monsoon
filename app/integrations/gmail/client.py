"""Gmail API client (readonly)."""

from __future__ import annotations

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Settings

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def build_gmail_service(settings: Settings):
    if not settings.gmail_configured:
        raise RuntimeError("Gmail not configured — set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN")

    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        scopes=GMAIL_SCOPES,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)
