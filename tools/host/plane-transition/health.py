#!/usr/bin/python3 -I
"""CTRL-HOST-005: fixed-project GET-only health, never a transition executor."""

import datetime
import fcntl
import importlib.util
import json
import os
import pwd
import resource
import signal
import sys

PROFILES = ("asrin", "selman", "batuhan", "yavuz")


def load_auto():
    spec = importlib.util.spec_from_file_location(
        "cap_auto_health", "/usr/local/libexec/cap-auto-next.py"
    )
    assert spec is not None and spec.loader is not None
    auto = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auto)
    return auto


def scan(auto, t, policy, plane, profiles):
    results = {}
    for profile in profiles:
        try:
            results[profile] = auto.owner_health(t, profile, policy, plane, t.GitHub)
        except Exception:
            results[profile] = {
                "current": None,
                "prepared_next": None,
                "health": "UNAVAILABLE",
                "first_blocker": None,
                "reasons": ["LIVE_OR_IDENTITY_SOURCE_UNAVAILABLE"],
            }
    return results


def report(results):
    return {
        "schema_version": "cap-plane-health-v1",
        "read_timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "project_health": "PROJECT_HEALTHY"
        if all(r["health"] == "HEALTHY" for r in results.values())
        else "PROJECT_STALL_RISK",
        "profiles": results,
    }


def emit(result, machine):
    if machine:
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    else:
        for profile, row in result["profiles"].items():
            print(profile)
            print("CURRENT:", (row.get("current") or {}).get("wp_id", "NONE"))
            print("PREPARED:", row.get("prepared_next") or "NONE")
            print("HEALTH:", row["health"])
            blocker = row.get("first_blocker")
            if blocker:
                print(
                    "NEXT_BLOCKER:",
                    blocker["wp_id"],
                    "/",
                    blocker["status"],
                    "/",
                    blocker["reason"],
                )
            elif row.get("reasons"):
                print("REASON:", "; ".join(row["reasons"]))


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    signal.alarm(180)
    args = sys.argv[1:]
    machine = "--json" in args
    profiles = list(PROFILES)
    try:
        if os.geteuid() != 0 or len(args) not in {1, 2} or len(set(args)) != len(args):
            raise ValueError()
        scope = [a for a in args if a != "--json"]
        if len(scope) != 1 or scope[0] not in {"--all", *PROFILES}:
            raise ValueError()
        caller = int(os.environ.get("SUDO_UID", str(os.getuid())))
        if scope[0] == "--all":
            if caller != 0:
                raise PermissionError()
        else:
            profiles = scope
            if caller not in {0, pwd.getpwnam(scope[0]).pw_uid}:
                raise PermissionError()
        os.environ.clear()
        auto = load_auto()
        t = auto.load_transition()
        policy = json.loads(
            (auto.ROOT / "transition-policy.json").read_text(),
            object_pairs_hook=t.q.unique,
        )
        t.verify_policy_sources(policy)
        t.policy_checks(policy)
        key = json.loads((auto.ROOT / "credential.json").read_text())["api_key"]
        fd = os.open(
            "/run/cap-plane-queue.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "r+") as lock:
            t.need(os.fstat(lock.fileno()).st_uid == 0, "UNSAFE_LOCK_OWNER")
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = report(scan(auto, t, policy, t.Plane(key), profiles))
        encoded = json.dumps(result)
        t.need(
            key not in encoded and json.dumps(key)[1:-1] not in encoded, "UNSAFE_OUTPUT"
        )
    except Exception:
        result = report(
            {
                p: {
                    "current": None,
                    "prepared_next": None,
                    "health": "UNAVAILABLE",
                    "first_blocker": None,
                    "reasons": ["PROFILE_POLICY_OR_LIVE_SOURCE_UNAVAILABLE"],
                }
                for p in profiles
            }
        )
    emit(result, machine)
    return (
        2
        if any(r["health"] == "UNAVAILABLE" for r in result["profiles"].values())
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
