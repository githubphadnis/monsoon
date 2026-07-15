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
import time

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.services.wa_backfill import ProgressEvent, WaBackfillService, index_counts


def _fmt_elapsed(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def _spinner(tick: int) -> str:
    return "|/-\\"[tick % 4]


def _bar(done: int, total: int | None, width: int = 18) -> str:
    if total and total > 0:
        filled = min(width, int(width * done / total))
        return "[" + "#" * filled + "-" * (width - filled) + "]"
    # Unknown total: bounce a blob so it still "moves"
    pos = done % max(1, width - 2)
    cells = ["-"] * width
    for i in range(3):
        if 0 <= pos + i < width:
            cells[pos + i] = "#"
    return "[" + "".join(cells) + "]"


class CliProgress:
    """TTY-friendly live progress; one line while paging, newline per finished chat."""

    def __init__(self, *, stream=None) -> None:
        self._stream = stream or sys.stderr
        self._t0 = time.monotonic()
        self._tick = 0
        self._last_len = 0
        self._isatty = bool(getattr(self._stream, "isatty", lambda: False)())

    def _write_live(self, text: str) -> None:
        pad = max(0, self._last_len - len(text))
        self._stream.write("\r" + text + (" " * pad))
        self._stream.flush()
        self._last_len = len(text)

    def _writeln(self, text: str) -> None:
        if self._last_len and self._isatty:
            self._stream.write("\r" + (" " * self._last_len) + "\r")
        self._stream.write(text + "\n")
        self._stream.flush()
        self._last_len = 0

    def __call__(self, ev: ProgressEvent) -> None:
        self._tick += 1
        elapsed = _fmt_elapsed(time.monotonic() - self._t0)
        chat_n = f"{ev.chats_done}/{ev.max_chats}" if ev.max_chats else f"{ev.chats_done}"
        bar = _bar(ev.chats_done, ev.max_chats)
        spin = _spinner(self._tick)
        totals = (
            f"+msgs={ev.messages_inserted} skip={ev.messages_skipped} "
            f"contacts=+{ev.contacts_upserted}  {elapsed}"
        )

        if ev.phase == "start":
            mode = ev.detail or "run"
            self._writeln(
                f"monsoon WA backfill  session={ev.session}  mode={mode}\n"
                f"(progress on this stream; JSON summary prints when done)"
            )
            return

        if ev.phase == "error":
            name = ev.chat_name or ev.chat_id or ""
            self._writeln(f"! error  {name}  {ev.detail}  | {totals}")
            return

        if ev.phase == "finished":
            self._writeln(
                f"{bar} done  chats={chat_n}  {totals}"
            )
            return

        name = (ev.chat_name or ev.chat_id or "?")[:40]
        if ev.phase == "chat_start":
            line = (
                f"{spin} {bar} chat {chat_n}  → {name}  "
                f"offset={ev.message_offset}  | {totals}"
            )
            if self._isatty:
                self._write_live(line)
            else:
                self._writeln(line)
            return

        if ev.phase == "chat_page":
            line = (
                f"{spin} {bar} chat {chat_n}  → {name}  "
                f"offset={ev.message_offset} (+{ev.page_messages})  "
                f"{ev.detail}  | {totals}"
            )
            if self._isatty:
                self._write_live(line)
            else:
                # Docker logs without TTY: only print every ~5 pages to avoid spam
                if (ev.message_offset // max(1, ev.page_messages or 100)) % 5 == 0:
                    self._writeln(line)
            return

        if ev.phase == "chat_done":
            mark = "✓" if ev.chat_complete else "…"
            self._writeln(
                f"{mark} {bar} chat {chat_n}  {name}  "
                f"{ev.detail}  | {totals}"
            )


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    init_db()
    session = (args.session or settings.waha_session).strip() or settings.waha_session

    if args.status:
        with SessionLocal() as db:
            counts = index_counts(db, session)
        print(json.dumps({"session": session, **counts}, indent=2))
        return 0

    progress = None if args.quiet else CliProgress()
    with SessionLocal() as db:
        service = WaBackfillService(
            db, settings, session=session, on_progress=progress
        )
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
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="No live progress (JSON summary only)",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
