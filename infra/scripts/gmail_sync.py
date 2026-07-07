#!/usr/bin/env python3
"""Sync Gmail into monsoon Postgres index.

Usage:
  docker exec monsoon-app python infra/scripts/gmail_sync.py --status
  docker exec monsoon-app python infra/scripts/gmail_sync.py --max-pages 2
  docker exec monsoon-app python infra/scripts/gmail_sync.py --full
"""

from __future__ import annotations

import argparse
import json
import sys

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.services.gmail_sync import GmailSyncService, gmail_index_counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Gmail → Postgres sync")
    parser.add_argument("--full", action="store_true", help="Reset cursors and re-list")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit list pages (pilot)")
    parser.add_argument("--status", action="store_true", help="Print index counts")
    args = parser.parse_args()

    settings = get_settings()
    init_db()

    if args.status:
        with SessionLocal() as db:
            counts = gmail_index_counts(db)
        print(
            json.dumps(
                {"configured": settings.gmail_configured, "label": settings.gmail_sync_label or "ALL", **counts},
                indent=2,
            )
        )
        return 0

    if not settings.gmail_configured:
        print("Gmail not configured. See docs/gmail-ingestion.md", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        stats = GmailSyncService(db, settings).run(full=args.full, max_pages=args.max_pages)

    print(
        json.dumps(
            {
                "threads_upserted": stats.threads_upserted,
                "messages_inserted": stats.messages_inserted,
                "messages_skipped": stats.messages_skipped,
                "participants_upserted": stats.participants_upserted,
                "entities_inserted": stats.entities_inserted,
                "errors": stats.errors,
            },
            indent=2,
        )
    )
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
