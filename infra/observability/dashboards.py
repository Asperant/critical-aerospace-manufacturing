"""Import the versioned OpenObserve dashboards (WP-OBS-001). Standard library only.

    python3 infra/observability/dashboards.py import

Reads O2_URL, O2_ROOT_EMAIL and O2_ROOT_PASSWORD (``stack.sh env``). Every
``dashboards/*.json`` file is created once in organization ``default``; a
dashboard whose title already exists is left untouched, so the command is
idempotent and never overwrites edits made in the UI. Exit 0 on success,
1 when OpenObserve rejects a dashboard, 2 on missing configuration.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ORG = "default"


def _call(method: str, url: str, auth: str, body: object = None) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw.strip() else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")[:300]


def definitions() -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((HERE / "dashboards").glob("*.json"))
    ]


def import_all(url: str, auth: str) -> int:
    status, listing = _call("GET", f"{url}/api/{ORG}/dashboards", auth)
    if status != 200 or not isinstance(listing, dict):
        print(f"cannot list dashboards: HTTP {status} {listing}", file=sys.stderr)
        return 1
    existing = {item.get("title") for item in listing.get("dashboards", [])}
    failed = False
    for dashboard in definitions():
        title = dashboard["title"]
        if title in existing:
            print(f"EXISTS   {title}")
            continue
        status, body = _call("POST", f"{url}/api/{ORG}/dashboards", auth, dashboard)
        if status in (200, 201):
            print(f"CREATED  {title}")
        else:
            failed = True
            print(f"REJECTED {title}: HTTP {status} {body}", file=sys.stderr)
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    if argv != ["import"]:
        print("usage: dashboards.py import", file=sys.stderr)
        return 2
    try:
        url = os.environ["O2_URL"].rstrip("/")
        token = f"{os.environ['O2_ROOT_EMAIL']}:{os.environ['O2_ROOT_PASSWORD']}"
    except KeyError as missing:
        print(
            f"{missing} is not set: run infra/observability/stack.sh env",
            file=sys.stderr,
        )
        return 2
    return import_all(url, "Basic " + base64.b64encode(token.encode()).decode())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
