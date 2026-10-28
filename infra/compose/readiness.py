"""WP-PLAT-003 — live view of the runtime readiness checklist (`stack.sh readiness`).

Reads readiness.json and reports, per 05 dependency edge, whether every service
that realizes it is running and healthy now. Exit status 1 when any HARD item has
a service that is missing or not healthy; SOFT items are reported only. This is a
health view: the readiness claim itself is the recorded run on the shared host.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def service_health(project: str) -> dict[str, str]:
    """Compose service -> "healthy", "starting", "unhealthy" or the container state.

    Read from Docker's own project labels, not through the Compose file: a stack
    whose file needs credentials to render (the observability stack) still reports.
    """
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--all",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            '{{.Label "com.docker.compose.service"}}\t{{.State}}\t{{.Status}}',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    health: dict[str, str] = {}
    for line in result.stdout.splitlines():
        service, state, status = line.split("\t", 2)
        if "(healthy)" in status:
            health[service] = "healthy"
        elif "(unhealthy)" in status:
            health[service] = "unhealthy"
        elif "(health: starting)" in status:
            health[service] = "starting"
        else:
            health[service] = state
    return health


def probe(url: str) -> str:
    """HTTP health surface of a service without a Docker health check."""
    url = re.sub(r"\$\{(\w+):-([^}]*)\}", lambda m: os.environ.get(m[1], m[2]), url)
    try:
        with urllib.request.urlopen(url, timeout=5):
            return "healthy"
    except (urllib.error.URLError, OSError):
        return "unreachable"


def main() -> int:
    checklist = json.loads((HERE / "readiness.json").read_text("utf-8"))
    health = {
        stack: service_health(project) for stack, project in checklist["stacks"].items()
    }
    failed = False
    for item in checklist["items"]:
        states = {}
        for service in item["services"]:
            if service in checklist.get("probes", {}):
                states[service] = (
                    probe(checklist["probes"][service]["url"])
                    if health[item["stack"]].get(service) == "running"
                    else health[item["stack"]].get(service, "missing")
                )
            else:
                states[service] = health[item["stack"]].get(service, "missing")
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
