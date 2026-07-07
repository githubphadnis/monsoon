"""Configure WAHA session webhook to point at monsoon.

Usage (on host with WAHA running):
  python infra/scripts/configure_waha_webhook.py \\
    --webhook-url http://127.0.0.1:8080/api/webhooks/waha
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure WAHA webhook for monsoon")
    parser.add_argument("--waha-url", default=os.getenv("WAHA_BASE_URL", "http://127.0.0.1:3000"))
    parser.add_argument("--api-key", default=os.getenv("WAHA_API_KEY", ""))
    parser.add_argument("--session", default=os.getenv("WAHA_SESSION", "default"))
    parser.add_argument("--webhook-url", required=True)
    args = parser.parse_args()

    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-Api-Key"] = args.api_key

    webhook: dict = {
        "url": args.webhook_url,
        "events": ["message", "message.any"],
    }
    if args.api_key:
        webhook["customHeaders"] = [{"name": "X-Api-Key", "value": args.api_key}]

    payload = {
        "name": args.session,
        "config": {
            "webhooks": [webhook],
        },
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{args.waha_url.rstrip('/')}/api/sessions", headers=headers, json=payload)
        if response.status_code >= 400:
            response = client.put(
                f"{args.waha_url.rstrip('/')}/api/sessions/{args.session}",
                headers=headers,
                json={"config": payload["config"]},
            )
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))

    with httpx.Client(timeout=30.0) as client:
        check = client.get(
            f"{args.waha_url.rstrip('/')}/api/sessions/{args.session}",
            headers=headers,
        )
        check.raise_for_status()
        webhooks = check.json().get("config", {}).get("webhooks", [])
        print(f"\nSession {args.session!r} webhooks configured: {len(webhooks)}")
        for hook in webhooks:
            print(f"  - {hook.get('url')} events={hook.get('events')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
