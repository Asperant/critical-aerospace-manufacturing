"""Deterministic probe matrix for WP-SCH-002; prints one JSON line, exit 0 iff ok.

Counts are reported separately and never merged into one pass rate. No clock, seed
or randomness is used: the instants below are fixed, and every payload is the
published snapshot fixture or a development RecoveryPlan fixture with a mutation.
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "services/scheduler-service/src"))

from manufacturing_scheduler.errors import ContractError  # noqa: E402
from manufacturing_scheduler.plans import (  # noqa: E402
    RecoveryPlan,
    check_snapshot_binding,
)
from manufacturing_scheduler.snapshot import (  # noqa: E402
    FreshnessMode,
    FreshnessPolicy,
    parse_snapshot,
)
from manufacturing_scheduler.wire import sha256_digest  # noqa: E402

SNAPSHOT = (
    REPO / "services/manufacturing-core/contracts/v1/scheduling-snapshot.normal.json"
)
PLANS = REPO / "services/scheduler-service/contracts/v1"
GENERATED = datetime(2026, 10, 27, 8, 0, tzinfo=UTC)
VALID_UNTIL = datetime(2026, 10, 27, 8, 5, tzinfo=UTC)
MICRO = timedelta(microseconds=1)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def freshness_table() -> list[dict[str, str]]:
    rows = []
    instants = {
        "generated-1us": GENERATED - MICRO,
        "generated": GENERATED,
        "valid_until-1us": VALID_UNTIL - MICRO,
        "valid_until": VALID_UNTIL,
        "valid_until+1h": VALID_UNTIL + timedelta(hours=1),
    }
    for status in ("FRESH", "DEGRADED", "STALE"):
        doc = load(SNAPSHOT)
        doc["freshness"]["status"] = status
        for label, now in instants.items():
            for mode in FreshnessMode:
                try:
                    snap = parse_snapshot(
                        doc,
                        expected_world_id="PRIMARY",
                        policy=FreshnessPolicy(now, mode),
                    )
                    outcome = f"{snap.usability.value}:{','.join(snap.diagnostics)}"
                except ContractError as exc:
                    outcome = f"REJECTED:{exc.code}"
                rows.append(
                    {
                        "status": status,
                        "now": label,
                        "mode": mode.value,
                        "outcome": outcome,
                    }
                )
    return rows


def leaves(node: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    if isinstance(node, dict):
        return [p for k, v in node.items() for p in leaves(v, (*path, k))]
    if isinstance(node, list):
        return [p for i, v in enumerate(node) for p in leaves(v, (*path, i))]
    return [path]


def tweak(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return "x"
    if isinstance(value, int | float):
        return value + 1
    return value + "x"


def redigest(doc: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in doc.items() if k != "content_digest"}
    return {**body, "content_digest": sha256_digest(body)}


def plan_mutations(name: str) -> dict[str, int]:
    original = load(PLANS / name)
    digest = RecoveryPlan.from_wire(original).content_digest
    counts = {
        "leaves": 0,
        "tampered_rejected": 0,
        "redigested_rejected": 0,
        "redigested_new_digest": 0,
        "redigested_same_digest": 0,
    }
    for path in leaves(original):
        counts["leaves"] += 1
        doc = copy.deepcopy(original)
        node: Any = doc
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = tweak(node[path[-1]])
        try:
            RecoveryPlan.from_wire(doc)
        except ContractError:
            counts["tampered_rejected"] += 1
        if path == ("content_digest",):
            continue
        try:
            decoded = RecoveryPlan.from_wire(redigest(doc))
        except ContractError:
            counts["redigested_rejected"] += 1
            continue
        counts[
            "redigested_new_digest"
            if decoded.content_digest != digest
            else "redigested_same_digest"
        ] += 1
    return counts


def binding_drift() -> dict[str, int]:
    plan = RecoveryPlan.from_wire(load(PLANS / "recovery-plan.v1.json"))
    base = load(SNAPSHOT)
    probes = {
        "revision": ("snapshot_revision",),
        "generated_at": ("generated_at",),
        "schedule": ("current_schedule_version",),
    }
    drifted = rejected = 0
    for keys in probes.values():
        doc = copy.deepcopy(base)
        doc[keys[0]] = "drifted-" + str(doc[keys[0]])
        drifted += 1
        try:
            check_snapshot_binding(
                plan,
                parse_snapshot(
                    doc,
                    expected_world_id="PRIMARY",
                    policy=FreshnessPolicy(GENERATED + timedelta(seconds=30)),
                ),
            )
        except ContractError:
            rejected += 1
    for table in ("lots", "equipment"):
        for index in range(len(base[table])):
            doc = copy.deepcopy(base)
            doc[table][index]["revision"] = "drifted"
            drifted += 1
            try:
                check_snapshot_binding(
                    plan,
                    parse_snapshot(
                        doc,
                        expected_world_id="PRIMARY",
                        policy=FreshnessPolicy(GENERATED + timedelta(seconds=30)),
                    ),
                )
            except ContractError:
                rejected += 1
    return {"drifted_snapshots": drifted, "rejected": rejected}


def main() -> int:
    table = freshness_table()
    mutations = {
        n: plan_mutations(n)
        for n in ("recovery-plan.v1.json", "recovery-plan.self-reported-valid.json")
    }
    binding = binding_drift()
    accepted_normal = [
        r for r in table if r["mode"] == "NORMAL" and r["outcome"].startswith("NORMAL")
    ]
    ok = (
        all(m["tampered_rejected"] == m["leaves"] for m in mutations.values())
        and all(m["redigested_same_digest"] == 0 for m in mutations.values())
        and binding["drifted_snapshots"] == binding["rejected"]
        # only FRESH snapshots strictly inside [generated_at, valid_until) are normal
        and {(r["status"], r["now"]) for r in accepted_normal}
        == {("FRESH", "generated"), ("FRESH", "valid_until-1us")}
    )
    report = {
        "ok": ok,
        "freshness_rows": len(table),
        "freshness_table": table,
        "plan_leaf_mutations": mutations,
        "binding_drift": binding,
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
