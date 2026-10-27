"""WP-PLAT-003 — live view of the runtime readiness checklist (`stack.sh readiness`).

Reads readiness.json and reports, per 05 dependency edge, whether every service
that realizes it is running and healthy now. Exit status 1 when any HARD item has
a service that is missing or not healthy; SOFT items are reported only. This is a
health view: the readiness claim itself is the recorded run on the shared host.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def service_health(stack: str) -> dict[str, str]:
    """Compose service -> Docker health ("healthy", "starting", ...) or state."""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(REPO / stack / "compose.yaml"),
            "ps",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    return {
        row["Service"]: row.get("Health") or row.get("State", "unknown") for row in rows
    }


def main() -> int:
    checklist = json.loads((HERE / "readiness.json").read_text("utf-8"))
    health = {
        stack: service_health(stack)
        for stack in {item["stack"] for item in checklist["items"]}
    }
    failed = False
    for item in checklist["items"]:
        states = {s: health[item["stack"]].get(s, "missing") for s in item["services"]}
        ok = all(state == "healthy" for state in states.values())
        failed |= not ok and item["strength"] == "HARD"
        bad = ", ".join(f"{s}={st}" for s, st in states.items() if st != "healthy")
        print(
            f"{'OK  ' if ok else 'WAIT'} {item['dep']} {item['consumer_node']:<15} "
            f"{item['strength']:<4} {item['required_readiness']:<17} by {item['need_by']}"
            + (f"  [{bad}]" if bad else "")
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
