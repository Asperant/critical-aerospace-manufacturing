"""DeploymentRecord: what one environment operation did and with what result.

02 (Release Manifest, normative statement 2): a deployment is SUCCEEDED only once
Preflight, Migration, Rollout, Health and Smoke have all passed; a container that is
running is not evidence of success. The validator enforces that, so a record cannot
claim more than its stages show.
"""

from __future__ import annotations

import datetime as dt
import secrets
from collections.abc import Mapping, Sequence
from typing import Any, cast

from cap_release.manifest import schema_problems

SCHEMA = "cap.deployment-record/v1"
STAGES = ("preflight", "migrate", "rollout", "health", "smoke")


def timestamp(moment: dt.datetime) -> str:
    return moment.astimezone(dt.UTC).isoformat(timespec="seconds")


def new_record_id(moment: dt.datetime) -> str:
    return f"DEP-REC-{moment.astimezone(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(4)}"


def stage(
    name: str,
    result: str,
    detail: str,
    started: dt.datetime | None = None,
    finished: dt.datetime | None = None,
) -> dict[str, Any]:
    return {
        "stage": name,
        "result": result,
        "started_at": timestamp(started) if started else None,
        "finished_at": timestamp(finished) if finished else None,
        "detail": detail,
    }


def not_run(name: str, why: str) -> dict[str, Any]:
    return stage(name, "NOT_RUN", why)


def validate_record(
    record: Mapping[str, Any], manifest: Mapping[str, Any] | None = None
) -> list[str]:
    """Schema and semantic problems of a record; empty means it tells the truth about itself."""
    problems = schema_problems("deployment-record.schema.json", record)
    stages = record.get("stages")
    if not isinstance(stages, list):
        return problems
    rows = [
        cast("dict[str, Any]", s)
        for s in cast("Sequence[Any]", stages)
        if isinstance(s, dict)
    ]
    names = [str(row.get("stage")) for row in rows]
    if names != list(STAGES):
        problems.append(f"stages must be exactly {list(STAGES)} in order, got {names}")
    results = {str(row.get("stage")): str(row.get("result")) for row in rows}
    migrate_bound = True
    if manifest is not None:
        target = manifest.get("database_schema_target")
        migrate_bound = (
            isinstance(target, dict)
            and cast("dict[str, Any]", target).get("state") == "BOUND"
        )
    result = record.get("result")
    if result == "SUCCEEDED":
        for name in STAGES:
            allowed: set[str] = {"PASSED"}
            if name == "migrate" and not migrate_bound:
                allowed = {"SKIPPED", "PASSED"}
            if results.get(name) not in allowed:
                problems.append(
                    f"SUCCEEDED needs stage {name} {'/'.join(sorted(allowed))}, got {results.get(name)}"
                )
        host = record.get("host_source")
        if isinstance(host, dict):
            source = cast("dict[str, Any]", host)
            if source.get("manual_patches") != 0:
                problems.append(
                    "SUCCEEDED needs zero manual source patches on the host (NFR-DEP-003)"
                )
            if source.get("checked_out_commit") != source.get("release_commit"):
                problems.append(
                    "SUCCEEDED needs the host checkout to equal the release commit"
                )
        chain = record.get("supply_chain_verification")
        if isinstance(chain, dict):
            verified = cast("dict[str, Any]", chain)
            if not (
                verified.get("main_derived") is True
                and verified.get("ci_gate") == "success"
                and verified.get("digests_in_registry") is True
            ):
                problems.append(
                    "SUCCEEDED needs a main-derived release, a green ci-gate and digests present in the registry"
                )
    elif result in {"FAILED", "ROLLED_BACK"}:
        if all(results.get(n) == "PASSED" for n in STAGES):
            problems.append(f"{result} but every stage passed")
    # A stage that did not pass must not be followed by one that ran.
    seen_stop = False
    for name in STAGES:
        outcome = results.get(name)
        if seen_stop and outcome in {"PASSED", "FAILED"}:
            problems.append(
                f"stage {name} ran after an earlier stage stopped the deployment"
            )
        if outcome in {"FAILED", "NOT_RUN"}:
            seen_stop = True
    if manifest is not None and record.get("release_id") != manifest.get("release_id"):
        problems.append("release_id differs from the manifest it deployed")
    return problems
