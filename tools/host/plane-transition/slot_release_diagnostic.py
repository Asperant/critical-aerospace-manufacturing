#!/usr/bin/python3 -I
"""CTRL-HOST-026: fixed, read-only Slot Release v2 diagnosis."""

import hashlib
import importlib.util
import json
import os
import resource
import sys
from pathlib import Path
from typing import Any

ROOT = Path("/etc/cap-plane-queue")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if os.geteuid() != 0 or len(sys.argv) != 3:
        raise RuntimeError()
    profile, wp = sys.argv[1:]
    auto: Any = load("/usr/local/libexec/cap-auto-next.py", "cap_slot_release_auto")
    auto.resolver = auto.load_resolver()
    t = auto.load_transition()
    policy = json.loads((ROOT / "transition-policy.json").read_text())
    t.verify_policy_sources(policy)
    t.policy_checks(policy)
    if profile not in auto.resolver.OWNERS or wp not in policy.get("contexts", {}):
        raise RuntimeError()
    caller = int(os.environ.get("SUDO_UID", "0"))
    auto.require_caller(profile, caller)
    gh = t.GitHub(profile)
    result = auto.semantic_slot_release_diagnose(t, wp, profile, policy, gh)
    result["installed_fingerprints"] = {
        "policy_digest": policy.get("policy_digest"),
        "auto_next_sha256": hashlib.sha256(
            Path("/usr/local/libexec/cap-auto-next.py").read_bytes()
        ).hexdigest(),
        "execution_queue_sha256": hashlib.sha256(
            Path("/usr/local/libexec/execution_queue.py").read_bytes()
        ).hexdigest(),
    }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            json.dumps(
                {
                    "schema": "cap-slot-release-diagnostic-v1",
                    "status": "UNAVAILABLE",
                    "reason": "LIVE_READ_OR_POLICY_VALIDATION_FAILED",
                },
                sort_keys=True,
            )
        )
        sys.exit(2)
