#!/usr/bin/env python3
"""Backfill WhatsApp history from WAHA into monsoon Postgres index.

Usage (on notcoolio):
  docker exec monsoon-app python infra/scripts/wa_backfill.py --status
  docker exec monsoon-app python infra/scripts/wa_backfill.py --status --session Rashmi
  docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5
  docker exec monsoon-app python infra/scripts/wa_backfill.py --full
  docker exec monsoon-app python infra/scripts/wa_backfill.py --full --session Prathamesh
  docker exec monsoon-app python infra/scripts/wa_backfill.py --chat-id 918291882204@c.us
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.services.wa_backfill import WaBackfillService, index_counts


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    init_db()
    session = (args.session or settings.waha_session).strip() or settings.waha_session

    if args.status:
        with SessionLocal() as db:
            counts = index_counts(db, session)
        print(json.dumps({"session": session, **counts}, indent=2))
        return 0

    with SessionLocal() as db:
        service = WaBackfillService(db, settings, session=session)
        stats = await service.run(
            full=args.full,
            max_chats=args.max_chats,
            chat_id=args.chat_id,
        )

    print(
        json.dumps(
            {
                "session": session,
                "chats_synced": stats.chats_synced,
                "chats_updated": stats.chats_updated,
                "messages_inserted": stats.messages_inserted,
                "messages_skipped": stats.messages_skipped,
                "contacts_upserted": stats.contacts_upserted,
                "entities_inserted": stats.entities_inserted,
                "errors": stats.errors,
            },
            indent=2,
        )
    )
    return 1 if stats.errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="WAHA → Postgres history backfill")
    parser.add_argument("--full", action="store_true", help="Reset per-chat offsets and re-walk")
    parser.add_argument("--max-chats", type=int, default=None, help="Limit chats processed")
    parser.add_argument("--chat-id", type=str, default=None, help="Sync one chat only")
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="WAHA session name (default: WAHA_SESSION / primary)",
    )
    parser.add_argument("--status", action="store_true", help="Print index counts and exit")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
