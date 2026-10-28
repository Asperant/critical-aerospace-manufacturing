"""Shared fixtures for the WP-SCH-002 tests (published contract files, fixed clock)."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from manufacturing_scheduler.snapshot import (
    FreshnessMode,
    FreshnessPolicy,
    PlanningSnapshot,
    parse_snapshot,
)
from manufacturing_scheduler.wire import sha256_digest

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_FIXTURE = (
    ROOT / "services/manufacturing-core/contracts/v1/scheduling-snapshot.normal.json"
)
PLAN_DIR = ROOT / "services/scheduler-service/contracts/v1"
NOW = datetime(2026, 10, 27, 8, 1, tzinfo=UTC)

Doc = dict[str, Any]


def load(path: Path) -> Doc:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_doc() -> Doc:
    return load(SNAPSHOT_FIXTURE)


def plan_doc(name: str = "recovery-plan.v1.json") -> Doc:
    return load(PLAN_DIR / name)


def policy(
    now: datetime = NOW, mode: FreshnessMode = FreshnessMode.NORMAL
) -> FreshnessPolicy:
    return FreshnessPolicy(now, mode)


def parsed_snapshot(doc: Doc | None = None) -> PlanningSnapshot:
    return parse_snapshot(
        doc or snapshot_doc(), expected_world_id="PRIMARY", policy=policy()
    )


def mutated(doc: Doc, change: Callable[[Doc], None]) -> Doc:
    clone = copy.deepcopy(doc)
    change(clone)
    return clone


def redigest(doc: Doc) -> Doc:
    """Recompute ``content_digest`` so a semantic defect cannot hide behind it."""

    clone = {key: value for key, value in doc.items() if key != "content_digest"}
    clone["content_digest"] = sha256_digest(clone)
    return clone
