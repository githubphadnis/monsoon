#!/usr/bin/env python3
"""Delete loop-spam tasks created by self-chat bot-echo feedback.

Usage (on notcoolio or with DATABASE_URL):
  python infra/scripts/cleanup_loop_tasks.py --dry-run
  python infra/scripts/cleanup_loop_tasks.py --apply
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from sqlalchemy import create_engine, text

# Match chained bot confirmation titles absorbed as task titles.
LOOP_TITLE_RE = re.compile(
    r"^(?:Task|Note) #\d+ created:.*(?:Task|Note) #\d+ created:",
    re.IGNORECASE,
)


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("Set DATABASE_URL", file=sys.stderr)
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove self-chat loop spam tasks")
    parser.add_argument("--apply", action="store_true", help="Delete matching rows")
    parser.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    args = parser.parse_args()
    dry_run = not args.apply

    engine = create_engine(_database_url(), pool_pre_ping=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id::text, display_number, title, created_at FROM tasks ORDER BY display_number"
            )
        ).fetchall()

        victims = [r for r in rows if LOOP_TITLE_RE.search(r.title or "")]
        print(f"Total tasks: {len(rows)}")
        print(f"Loop-spam candidates: {len(victims)}")
        for row in victims[:20]:
            title = (row.title or "")[:70]
            print(f"  #{row.display_number} {title}...")
        if len(victims) > 20:
            print(f"  ... and {len(victims) - 20} more")

        if dry_run:
            print("\nDry run — pass --apply to delete.")
            return 0

        if not victims:
            print("Nothing to delete.")
            return 0

        ids = [r.id for r in victims]
        conn.execute(
            text("DELETE FROM task_events WHERE task_id = ANY(:ids)"),
            {"ids": ids},
        )
        conn.execute(
            text("DELETE FROM tasks WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
        conn.commit()
        print(f"Deleted {len(victims)} tasks and their events.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
