"""AUTO_NEXT canonical selection regression tests; no network or mutations."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from projectctl.execution_queue import (
    ACTIVE,
    ASSIGNEES,
    EXCLUDED,
    OWNERS,
    RTM_PATH,
    WBS_PATH,
    affected_owners,
    compute_next_eligible,
    project_view,
    scope_projection,
    validate_preferences,
)
from projectctl.project import load_project

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def baseline():
    project = project_view(load_project(ROOT))
    policy = yaml.safe_load(
        (ROOT / "project_control/execution_preferences.yaml").read_text()
    )
    live = {
        "complete": True,
        "items": {
            wp: {
                "owner": c["owner"],
                "assignees": [ASSIGNEES[c["owner"]]],
                "state": "BACKLOG",
                "blocked": False,
            }
            for wp, c in project["cards"].items()
        },
    }
    evidence = {
        "complete": True,
        "source_manifest": project["source_manifest"],
        "candidates": {},
    }
    return project, policy, live, evidence


def evaluate(data, owner="asrin"):
    project, policy, live, evidence = data
    return compute_next_eligible(project, live, evidence, owner, policy)


def qualify(data, wp):
    project, _, _, evidence = data
    evidence["candidates"][wp] = {
        "result": "PASS",
        "dor": "PASS",
        "evidence_refs": ["comment:1"],
        "dependencies": {
            e["id"]: {
                "result": "PASS",
                "readiness": e["semantics"]["required_readiness"],
                "precise_consumer_requirement": "Exact consumer contract fields",
                "evidence_refs": ["repo:evidence/fixture.md"],
            }
            for e in project["cards"][wp]["edges"]
        },
    }


def test_full_counts_and_ownership(baseline):
    project, policy, _, _ = baseline
    assert len(project["cards"]) == 179
    assert sum(c["scheduled"] for c in project["cards"].values()) == 174
    assert {w for w, c in project["cards"].items() if not c["scheduled"]} == EXCLUDED
    assert [len(policy["sequences"][o]) for o in OWNERS.values()] == [69, 17, 32, 56]
    assert validate_preferences(project, policy) == []


@pytest.mark.parametrize(
    "mutation", ["duplicate", "missing", "unknown", "foreign", "optional"]
)
def test_preference_invalid(baseline, mutation):
    data = deepcopy(baseline)
    seq = data[1]["sequences"][OWNERS["asrin"]]
    if mutation == "duplicate":
        seq.append(seq[0])
    elif mutation == "missing":
        seq.pop()
    elif mutation == "unknown":
        seq[0] = "WP-UNKNOWN-001"
    elif mutation == "foreign":
        seq[0] = data[1]["sequences"][OWNERS["selman"]][0]
    else:
        seq[0] = "WP-R2-001"
    assert evaluate(data)["status"] == "INVALID_BASELINE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("owner", OWNERS["selman"]),
        ("assignees", []),
        ("assignees", ["wrong"]),
        ("assignees", [ASSIGNEES[OWNERS["asrin"]], "wrong"]),
    ],
)
def test_live_identity_fails_closed(baseline, field, value):
    data = deepcopy(baseline)
    data[2]["items"]["WP-CORE-001"][field] = value
    assert evaluate(data)["status"] == "INVALID_BASELINE"


@pytest.mark.parametrize("state", sorted(ACTIVE))
def test_active_pending_prevents_another_ready(baseline, state):
    data = deepcopy(baseline)
    data[2]["items"]["WP-CORE-001"]["state"] = state
    result = evaluate(data)
    assert result["wp_id"] == "WP-CORE-001"
    assert result["status"] == ("READY" if state == "READY" else "CURRENT")


def test_blocked_active_is_not_replaced(baseline):
    data = deepcopy(baseline)
    data[2]["items"]["WP-CORE-001"].update(
        state="IN_REVIEW", blocked=True, blocker_reason="Waiting on exact contract"
    )
    assert evaluate(data)["status"] == "BLOCKED"
    assert evaluate(data)["reasons"] == ["Waiting on exact contract"]


def test_multiple_active_unavailable(baseline):
    data = deepcopy(baseline)
    for wp in ("WP-CORE-001", "WP-CORE-002"):
        data[2]["items"][wp]["state"] = "READY"
    assert evaluate(data)["status"] == "UNAVAILABLE"


@pytest.mark.parametrize("state", ["DONE", "CANCELED"])
def test_terminal_excluded(baseline, state):
    data = deepcopy(baseline)
    wp = data[1]["sequences"][OWNERS["asrin"]][0]
    qualify(data, wp)
    data[2]["items"][wp]["state"] = state
    assert evaluate(data)["wp_id"] is None


def test_first_blocked_second_valid_and_multiple_eligible(baseline):
    data = deepcopy(baseline)
    first, second = data[1]["sequences"][OWNERS["asrin"]][:2]
    qualify(data, first)
    qualify(data, second)
    data[2]["items"][first]["blocked"] = True
    assert evaluate(data)["wp_id"] == second
    data[2]["items"][first]["blocked"] = False
    assert evaluate(data)["wp_id"] == first


def test_no_lexical_or_import_order_fallback(baseline):
    data = deepcopy(baseline)
    seq = data[1]["sequences"][OWNERS["asrin"]]
    seq.reverse()
    for wp in seq:
        qualify(data, wp)
    assert evaluate(data)["wp_id"] == seq[0]
    assert seq[0] != sorted(seq)[0]


def test_unknown_is_not_pass_and_skip_reasons(baseline):
    data = deepcopy(baseline)
    first = data[1]["sequences"][OWNERS["asrin"]][0]
    data[3]["candidates"][first] = {
        "result": "UNKNOWN",
        "dor": "PASS",
        "evidence_refs": ["comment:1"],
    }
    result = evaluate(data)
    assert result["status"] == "NO_TASK"
    assert result["considered"][0]["reason"] == "DOR_EVIDENCE_UNKNOWN"


def test_start_gate_producer_done_insufficient(baseline):
    data = deepcopy(baseline)
    wp = "WP-CORE-002"
    qualify(data, wp)
    data[3]["candidates"][wp]["dependencies"] = {}
    data[2]["items"]["WP-CORE-001"]["state"] = "DONE"
    assert evaluate(data)["status"] == "NO_TASK"
    assert any(
        "HARD_START_READINESS_UNKNOWN" in (r["reason"] or "")
        for r in evaluate(data)["considered"]
    )


@pytest.mark.parametrize("stage", ["INTEGRATION", "MILESTONE_EXIT", "FREEZE"])
def test_later_stage_not_start_gate(baseline, stage):
    data = deepcopy(baseline)
    wp = data[1]["sequences"][OWNERS["asrin"]][0]
    data[0]["cards"][wp]["edges"] = [
        {
            "id": "DEP-TEST",
            "predecessor": {"node": "UNKNOWN_NODE"},
            "semantics": {
                "strength": "HARD",
                "blocking_stage": stage,
                "required_readiness": "FROZEN",
            },
        }
    ]
    qualify(data, wp)
    data[3]["candidates"][wp]["dependencies"] = {}
    assert evaluate(data)["wp_id"] == wp


def test_soft_gap_visible(baseline):
    data = deepcopy(baseline)
    wp = data[1]["sequences"][OWNERS["asrin"]][0]
    data[0]["cards"][wp]["edges"] = [
        {
            "id": "DEP-SOFT",
            "semantics": {"strength": "SOFT", "blocking_stage": "START"},
        }
    ]
    data[3]["candidates"][wp] = {
        "result": "PASS",
        "dor": "PASS",
        "evidence_refs": ["comment:1"],
    }
    result = evaluate(data)
    assert result["wp_id"] == wp
    assert result["considered"][0]["soft_dependencies"] == ["DEP-SOFT"]


@pytest.mark.parametrize("kind", ["partial", "unknown_state", "source", "evidence"])
def test_unavailable_inputs_no_selection(baseline, kind):
    data = deepcopy(baseline)
    if kind == "partial":
        data[2]["items"].pop("WP-CORE-001")
    elif kind == "unknown_state":
        data[2]["items"]["WP-CORE-001"]["state"] = "TRIAGE"
    elif kind == "source":
        data[3]["source_manifest"] = {}
    else:
        data[3]["complete"] = False
    assert evaluate(data)["status"] == "UNAVAILABLE"


def test_cross_owner_affected_not_all(baseline):
    project = baseline[0]
    owners = affected_owners(project, "WP-VDATA-003")
    assert OWNERS["selman"] in owners
    assert OWNERS["yavuz"] not in owners
    assert affected_owners(project, "WP-AI-005") == [OWNERS["asrin"]]


def test_pure_and_deterministic(baseline):
    data = deepcopy(baseline)
    before = deepcopy(data)
    assert evaluate(data) == evaluate(data)
    assert data == before


def defer(data):
    wp = "WP-CORE-001"
    data[2]["items"][wp].update(
        state="VALIDATING",
        blocked=True,
        deferred_acceptance={
            "schema": "cap-deferred-acceptance-v1",
            "wp_id": wp,
            "owner": OWNERS["asrin"],
            "classification": "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE",
            "implementation_complete": True,
            "owner_work_remaining": False,
            "merge_sha": "a" * 40,
            "audit_id": "b" * 64,
            "assessment_digest": "c" * 64,
        },
    )
    return data[2]["items"][wp]


def test_deferred_release_preference_one_ready_and_other_owners_unchanged(baseline):
    data = deepcopy(baseline)
    defer(data)
    seq = [w for w in data[1]["sequences"][OWNERS["asrin"]] if w != "WP-CORE-001"]
    for wp in seq[:2]:
        qualify(data, wp)
    before = deepcopy(data)
    foreign = {o: evaluate(data, o) for o in ("selman", "batuhan", "yavuz")}
    result = evaluate(data)
    assert result["status"] == "PROPOSED_NEXT"
    assert result["wp_id"] == seq[0]
    assert data == before  # resolver read-only, canonical order unchanged
    data[2]["items"][seq[0]]["state"] = "READY"
    assert evaluate(data)["status"] == "READY"
    assert evaluate(data)["wp_id"] == seq[0]  # no second READY
    assert foreign == {o: evaluate(data, o) for o in foreign}
    assert data[2]["items"]["WP-CORE-001"]["state"] == "VALIDATING"


@pytest.mark.parametrize(
    "mutation",
    ["ordinary", "implementation", "unknown", "work", "owner", "missing", "unblocked"],
)
def test_deferred_unknown_or_local_work_retains_slot(baseline, mutation):
    data = deepcopy(baseline)
    item = defer(data)
    proof = item["deferred_acceptance"]
    if mutation == "ordinary":
        item.pop("deferred_acceptance")
    elif mutation in {"implementation", "unknown"}:
        proof["classification"] = mutation.upper()
    elif mutation == "work":
        proof["owner_work_remaining"] = True
    elif mutation == "owner":
        proof["owner"] = OWNERS["selman"]
    elif mutation == "missing":
        proof.pop("assessment_digest")
    else:
        item["blocked"] = False
    assert evaluate(data)["status"] in {"BLOCKED", "CURRENT"}
    assert evaluate(data)["wp_id"] == "WP-CORE-001"


@pytest.mark.parametrize("state", sorted(ACTIVE - {"VALIDATING"}))
def test_deferred_proof_cannot_exempt_other_active_states(baseline, state):
    data = deepcopy(baseline)
    defer(data)["state"] = state
    assert evaluate(data)["status"] == "BLOCKED"


def test_deferred_does_not_hide_another_active_or_duplicate_ready(baseline):
    data = deepcopy(baseline)
    defer(data)
    data[2]["items"]["WP-CORE-002"]["state"] = "IN_PROGRESS"
    assert evaluate(data)["wp_id"] == "WP-CORE-002"
    data[2]["items"]["WP-CORE-003"]["state"] = "READY"
    assert evaluate(data)["reasons"] == ["MULTIPLE_ACTIVE_WORK"]


def test_deferred_health_visible_but_not_implementation_blocker(baseline):
    from projectctl.execution_queue import preflight_health

    data = deepcopy(baseline)
    defer(data)
    data[2]["items"]["WP-CORE-002"]["state"] = "READY"
    qualify(data, "WP-CORE-003")
    p, prefs, live, evidence = data
    result = preflight_health(p, live, evidence, "asrin", prefs)
    assert result["current"]["wp_id"] == "WP-CORE-002"
    assert result["deferred_waits"][0]["wp_id"] == "WP-CORE-001"
    assert result["health"] == "HEALTHY"


def scope_docs(own="own", other="other", wp="WP-AAA-001"):
    wbs = (
        f"| {wp} | Title | Owner |\n| WP-BBB-001 | {other} | Owner |\n\n"
        f"#### {wp} — Title\n\n{own}\n\n##### Sub\n\n{own}-sub\n\n"
        f"#### WP-BBB-001 — Other\n\n{other}\n"
    )
    rtm = (
        f"| FR-AAA-001 | F0 | {own} |\n| FR-BBB-001 | F0 | {other} |\n\n"
        f"FR-AAA-001:\n  meta: {{{own}}}\n  state: x\n\n"
        f"FR-BBB-001:\n  meta: {{{other}}}\n"
    )
    return wbs, rtm


def projection(wbs, rtm, refs=("FR-AAA-001",), wp="WP-AAA-001"):
    return scope_projection(wp, list(refs), wbs, rtm)


def test_scope_projection_ignores_unrelated_shared_file_edits():
    base = projection(*scope_docs())
    assert projection(*scope_docs(other="changed elsewhere")) == base
    wbs, rtm = scope_docs()
    assert (
        projection(
            wbs + "\n#### WP-CCC-001 — New\n\nnew\n", rtm + "\nFR-CCC-001:\n  x: 1\n"
        )
        == base
    )
    assert projection(wbs.replace("\r", ""), rtm.replace("\n", "\r\n")) == base


@pytest.mark.parametrize(
    "field", ["wbs_row", "wbs_card", "wbs_sub", "rtm_row", "rtm_block"]
)
def test_scope_projection_detects_own_scope_edits(field):
    wbs, rtm = scope_docs()
    base = projection(wbs, rtm)
    if field == "wbs_row":
        wbs = wbs.replace("| WP-AAA-001 | Title |", "| WP-AAA-001 | Retitled |")
    elif field == "wbs_card":
        wbs = wbs.replace("\nown\n", "\nown changed\n", 1)
    elif field == "wbs_sub":
        wbs = wbs.replace("own-sub", "own-sub changed")
    elif field == "rtm_row":
        rtm = rtm.replace("| FR-AAA-001 | F0 |", "| FR-AAA-001 | F1 |")
    else:
        rtm = rtm.replace("state: x", "state: y")
    assert projection(wbs, rtm) != base


def test_scope_projection_requirement_set_is_part_of_scope():
    wbs, rtm = scope_docs()
    assert projection(wbs, rtm, ("FR-AAA-001", "FR-BBB-001")) != projection(wbs, rtm)
    assert projection(
        wbs, rtm, ("FR-BBB-001", "FR-AAA-001", "FR-AAA-001")
    ) == projection(wbs, rtm, ("FR-AAA-001", "FR-BBB-001"))


@pytest.mark.parametrize(
    "case",
    [
        "no_card",
        "duplicate_card",
        "no_row",
        "no_rtm_row",
        "no_rtm_block",
        "duplicate_rtm_block",
        "no_refs",
        "bad_ref",
        "bad_wp",
    ],
)
def test_scope_projection_fails_closed_when_missing_or_ambiguous(case):
    wbs, rtm = scope_docs()
    refs, wp = ("FR-AAA-001",), "WP-AAA-001"
    if case == "no_card":
        wbs = wbs.replace("#### WP-AAA-001 — Title", "#### Renamed")
    elif case == "duplicate_card":
        wbs += "\n#### WP-AAA-001 — Title\n\ncopy\n"
    elif case == "no_row":
        wbs = wbs.replace("| WP-AAA-001 |", "| WP-ZZZ-001 |")
    elif case == "no_rtm_row":
        rtm = rtm.replace("| FR-AAA-001 |", "| FR-ZZZ-001 |")
    elif case == "no_rtm_block":
        rtm = rtm.replace("FR-AAA-001:", "FR-ZZZ-001:")
    elif case == "duplicate_rtm_block":
        rtm += "\nFR-AAA-001:\n  meta: copy\n"
    elif case == "no_refs":
        refs = ()
    elif case == "bad_ref":
        refs = ("not a requirement",)
    else:
        wp = "WP-1"
    with pytest.raises(ValueError):
        scope_projection(wp, list(refs), wbs, rtm)


def test_scope_projection_covers_every_canonical_work_package():
    project = load_project(ROOT)
    wbs = (ROOT / WBS_PATH).read_text()
    rtm = (ROOT / RTM_PATH).read_text()
    digests = {
        w.id: scope_projection(w.id, list(w.requirement_refs or []), wbs, rtm)
        for w in project.catalog.work_packages
    }
    assert len(digests) == len(project.catalog.work_packages) > 100
    assert all(len(d) == 64 for d in digests.values())
