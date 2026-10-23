#!/usr/bin/python3 -I
"""Persist bounded sanitized health only. Never invoke a Plane writer."""

import datetime
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    if os.geteuid() != 0:
        return 2
    os.umask(0o077)
    result = {
        "schema_version": "cap-plane-health-v1",
        "project_health": "PROJECT_STALL_RISK",
        "read_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "status": "UNAVAILABLE",
        "profiles": {},
    }
    try:
        run = subprocess.run(
            ["/usr/local/bin/cap-plane-health", "--all", "--json"],
            capture_output=True,
            timeout=210,
            check=False,
        )
        if run.returncode not in {0, 2} or len(run.stdout) > 2_000_000:
            raise ValueError()
        data = json.loads(run.stdout)
        if (
            data.get("schema_version") != "cap-plane-health-v1"
            or data.get("project_health")
            not in {"PROJECT_HEALTHY", "PROJECT_STALL_RISK"}
            or set(data.get("profiles", {})) != {"asrin", "selman", "batuhan", "yavuz"}
        ):
            raise ValueError()
        result = data
    except Exception:
        pass
    state = Path("/var/lib/cap-plane-health")
    state.mkdir(mode=0o700, exist_ok=True)
    if state.is_symlink() or state.stat().st_uid != 0 or state.stat().st_mode & 0o077:
        return 2
    fd, temp_name = tempfile.mkstemp(prefix="health-", suffix=".json", dir=state)
    temp = Path(temp_name)
    with os.fdopen(fd, "w") as stream:
        json.dump(result, stream, ensure_ascii=True, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, state / "latest.json")
    unavailable = result.get("status") == "UNAVAILABLE" or any(
        r["health"] == "UNAVAILABLE" for r in result["profiles"].values()
    )
    print(
        json.dumps(
            {
                "project_health": result["project_health"],
                "result": "UNAVAILABLE" if unavailable else "REFRESHED",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
