#!/usr/bin/env python3
"""Create GitHub issues from docs/roadmap_issues.csv.

Usage:
  python scripts/create_roadmap_issues.py
  python scripts/create_roadmap_issues.py --apply
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


def _build_command(row: dict[str, str]) -> list[str]:
    title = (row.get("title") or "").strip()
    body = (row.get("body") or "").strip()
    labels = [x.strip() for x in (row.get("labels") or "").split(",") if x.strip()]
    milestone = (row.get("milestone") or "").strip()

    if not title:
        raise ValueError("CSV row missing required title.")

    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        "githubphadnis/monsoon",
        "--title",
        title,
        "--body",
        body,
    ]
    for label in labels:
        cmd.extend(["--label", label])
    if milestone:
        cmd.extend(["--milestone", milestone])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="docs/roadmap_issues.csv",
        help="Path to issue CSV file.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create issues. Without this flag, only prints commands.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit("No rows found in CSV.")

    for row in rows:
        cmd = _build_command(row)
        print("$", " ".join(cmd).encode("ascii", "backslashreplace").decode("ascii"))
        if args.apply:
            subprocess.run(cmd, check=True)

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"Completed in {mode} mode with {len(rows)} issue rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
