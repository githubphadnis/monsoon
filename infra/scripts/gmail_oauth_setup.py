#!/usr/bin/env python3
"""One-time OAuth setup — run on your PC to obtain GMAIL_REFRESH_TOKEN.

Prerequisites:
  1. Google Cloud project with Gmail API enabled
  2. OAuth client ID (Desktop app) — download JSON or set env vars

Usage:
  pip install google-auth-oauthlib google-api-python-client
  export GMAIL_CLIENT_ID=...
  export GMAIL_CLIENT_SECRET=...
  python infra/scripts/gmail_oauth_setup.py

Or:
  python infra/scripts/gmail_oauth_setup.py --client-secrets path/to/client_secret.json

Prints refresh token — paste into Portainer as GMAIL_REFRESH_TOKEN (secret).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Obtain Gmail OAuth refresh token")
    parser.add_argument("--client-secrets", help="Path to OAuth client JSON from Google Cloud")
    args = parser.parse_args()

    if args.client_secrets:
        flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
    else:
        client_id = os.getenv("GMAIL_CLIENT_ID", "")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            print("Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET or pass --client-secrets", file=sys.stderr)
            return 1
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            },
            SCOPES,
        )

    creds = flow.run_local_server(port=0)
    print("\nAdd to Portainer stack env:\n")
    print(f"GMAIL_CLIENT_ID={creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("\n(JSON)")
    print(
        json.dumps(
            {
                "GMAIL_CLIENT_ID": creds.client_id,
                "GMAIL_CLIENT_SECRET": creds.client_secret,
                "GMAIL_REFRESH_TOKEN": creds.refresh_token,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
