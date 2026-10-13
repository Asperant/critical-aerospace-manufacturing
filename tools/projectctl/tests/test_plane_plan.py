from copy import deepcopy
import json
import socket

import pytest
from typer.testing import CliRunner

from projectctl.cli import app
from projectctl.plane import PlaneError
from projectctl.plane_plan import STATES, bootstrap_plan
from projectctl.project import load_project


@pytest.fixture
def project(root):
    return load_project(root)


@pytest.fixture
def audit():
    return {"schema_version": "plane-v1-audit-v1", "api_version": "v1", "mutation_enabled": False,
            "workspace": {"id": "w", "slug": "workspace"},
            "project": {"id": "project", "name": "Graduation Project", "identifier": "CAP"},
            "states": [{"id": s, "name": s} for s in STATES],
            "labels": [{"id": "blocked", "name": "BLOCKED"}], "modules": [], "cycles": [], "work_items": [],
            "project_members": [{"id": "asrin", "first_name": "asrın", "last_name": "dündar"}],
            "workspace_members": []}


def test_full_dry_run_counts_mappings_and_determinism(project, audit):
    before = deepcopy(audit)
    plan = bootstrap_plan(project, audit)
    assert audit == before and plan == bootstrap_plan(project, audit)
    assert plan["mutation_enabled"] is False and plan["dry_run"] is True
    assert plan["summary"] == {"actions": {"create": 230, "unchanged": 1}, "modules": 29, "cycles": 13,
                              "milestone_labels": 9, "work_packages": 179, "scheduled": 174,
                              "unscheduled_ids": ["WP-R2-001", "WP-R2-002", "WP-R2-003", "WP-S-001", "WP-X-001"]}
    assert plan["owner_mapping"]["Asrın Dündar"] == "asrin"
    assert len(plan["missing_owners"]) == 3
    assert len(plan["ambiguous_mappings"]) == 117
    assert not plan["ready_for_live_mutation"]
    items = [o for o in plan["operations"] if o["kind"] == "work_items"]
    assert all(o["request"]["body"]["state"] == "BACKLOG" for o in items)
    assert sum("assignees" in o["request"]["body"] for o in items) == 73
    assert all(o["relations"]["cycle"] is None for o in items if o["identity"] in plan["summary"]["unscheduled_ids"])
    assert all(o["relations"]["cycle"] is None and o["blockers"] for o in items
               if len(o["canonical_metadata"]["cycle_ids"]) == 2)
    assert {o["desired"]["name"] for o in plan["operations"] if o["kind"] == "cycles"} == {f"S{i}" for i in range(1,14)}
    assert not any("start_date" in o["desired"] or "end_date" in o["desired"] for o in plan["operations"])


def test_projection_idempotency_after_simulated_apply_and_state_preservation(project, audit):
    first = bootstrap_plan(project, audit)
    for op in first["operations"]:
        if op["action"] == "create":
            audit[op["kind"]].append({"id": "fake-" + op["identity"], **deepcopy(op["desired"])})
    audit["work_items"][0]["state"] = "IN_PROGRESS"
    second = bootstrap_plan(project, audit)
    assert second["summary"]["actions"] == {"unchanged": 231}
    assert all(o["request"] is None for o in second["operations"])
    assert audit["work_items"][0]["state"] == "IN_PROGRESS"
    # This proves static projection identity; unknown live relations remain explicit blockers.
    assert any(a["code"] == "RELATION_READ_REQUIRED" for a in second["ambiguous_mappings"])


def test_duplicates_and_identity_conflicts_never_title_match(project, audit):
    audit["work_items"] = [{"id": "one", "name": "[WP-CORE-001] old title", "external_id": "WP-CORE-002"},
                           {"id": "two", "name": "[WP-CORE-001] other title"},
                           {"id": "unmanaged", "name": project.catalog.work_packages[0].title},
                           {"id": "unknown", "name": "[WP-UNKNOWN-001] unexpected"}]
    audit["modules"] = [{"id": "a", "name": "WP-CORE"}, {"id": "b", "name": "WP-CORE"}]
    plan = bootstrap_plan(project, audit)
    assert plan["duplicate_canonical_ids"] == {"WP-CORE-001": ["one", "two"]}
    assert plan["unmanaged_work_items"] == ["unmanaged"]
    codes = {c["code"] for c in plan["conflicts"]}
    assert {"DUPLICATE_CANONICAL_ID", "CONFLICTING_CANONICAL_IDS", "DUPLICATE_STRUCTURE", "UNKNOWN_CANONICAL_ID"} <= codes
    assert next(o for o in plan["operations"] if o["identity"] == "WP-CORE-001")["request"] is None


def test_exact_workflow_names_and_no_guessing_members(project, audit):
    audit["states"] = [s for s in audit["states"] if s["name"] != "IN_REVIEW"] + [{"id": "typo", "name": "IN_REVİEW"}]
    audit["project_members"].append({"id": "wrong", "display_name": "Selman Özdemir", "first_name": "Selman", "last_name": "Different"})
    plan = bootstrap_plan(project, audit)
    assert len(plan["conflicts"]) == 2
    assert plan["owner_mapping"]["Selman Özdemir"] is None
    assert {c["identity"] for c in plan["conflicts"]} == {"IN_REVIEW", "IN_REVİEW"}


def test_static_updates_never_reset_state_or_overwrite_unmanaged_text(project, audit):
    first = bootstrap_plan(project, audit)
    item = next(o for o in first["operations"] if o["kind"] == "work_items")
    audit["work_items"] = [{"id": "owned", **deepcopy(item["desired"]), "state": "DONE"}]
    audit["work_items"][0]["name"] = f"[{item['identity']}] stale title"
    plan = bootstrap_plan(project, audit)
    op = next(o for o in plan["operations"] if o["identity"] == item["identity"])
    assert op["action"] == "update" and op["request"]["body"] == {"name": item["desired"]["name"]}
    audit["work_items"][0]["external_source"] = None
    op = next(o for o in bootstrap_plan(project, audit)["operations"] if o["identity"] == item["identity"])
    assert op["action"] == "conflict" and op["request"] is None


def test_wrong_target_and_canonical_failure_block(project, audit):
    wrong = deepcopy(audit)
    wrong["project"]["identifier"] = "OTHER"
    with pytest.raises(PlaneError, match="wrong-target"):
        bootstrap_plan(project, wrong)
    broken = deepcopy(project)
    broken.catalog.work_packages.pop()
    with pytest.raises(PlaneError, match="Canonical validation failed"):
        bootstrap_plan(broken, audit)


def test_plan_cli_is_offline_and_writes_only_stdout(root, audit, tmp_path, monkeypatch):
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(audit))
    def forbidden(*args, **kwargs):
        raise AssertionError("Network or writable file opened")
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    import io
    original = io.open
    def guarded(path, mode="r", *args, **kwargs):
        if any(c in mode for c in "wax+"):
            forbidden()
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(io, "open", guarded)
    result = CliRunner().invoke(app, ["plane-plan", "--audit", str(path), "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["dry_run"] is True
