"""Focused derived-health regressions using the real canonical fixture."""

from copy import deepcopy

import pytest
from projectctl.execution_queue import OWNERS, compute_next_eligible, preflight_health
from test_execution_queue import qualify

pytest_plugins = ["test_execution_queue"]


def health(data):
    project, policy, live, evidence = data
    return preflight_health(project, live, evidence, "asrin", policy)


def setup(baseline, current=True):
    data = deepcopy(baseline)
    seq = data[1]["sequences"][OWNERS["asrin"]]
    if current:
        data[2]["items"][seq[0]]["state"] = "READY"
    return data, seq


def test_current_and_prepared_preserves_inputs_and_release_guard(baseline):
    data, seq = setup(baseline)
    qualify(data, seq[1])
    before = deepcopy(data)
    result = health(data)
    assert result["health"] == "HEALTHY"
    assert result["prepared_next"] == seq[1]
    assert data == before
    assert (
        compute_next_eligible(data[0], data[2], data[3], "asrin", data[1])["wp_id"]
        == seq[0]
    )


@pytest.mark.parametrize("current,expected", [(True, "STALL_RISK"), (False, "STALLED")])
def test_no_buffer(baseline, current, expected):
    data, _ = setup(baseline, current)
    result = health(data)
    assert result["health"] == expected
    assert result["prepared_next"] is None
    assert len(result["candidates"]) == 3
    assert result["first_blocker"]["status"] == "NEEDS_DOR"


def test_unknown_never_prepared(baseline):
    data, seq = setup(baseline)
    qualify(data, seq[1])
    data[3]["candidates"][seq[1]]["result"] = "UNKNOWN"
    assert health(data)["prepared_next"] is None


def test_later_eligible_after_blocked_and_unknown(baseline):
    data, seq = setup(baseline)
    data[2]["items"][seq[1]]["blocked"] = True
    qualify(data, seq[3])
    assert health(data)["prepared_next"] == seq[3]
    assert health(data)["candidates"][0]["status"] == "BLOCKED"


def test_later_cycle_and_beyond_top_three_not_gated(baseline):
    data, seq = setup(baseline)
    qualify(data, seq[-1])
    data[0]["cards"][seq[-1]]["cycle"] = "S13"
    assert health(data)["prepared_next"] == seq[-1]


def test_cross_owner_hard_start_node_diagnostics(baseline):
    data, seq = setup(baseline)
    edge = {
        "id": "DEP-TEST",
        "predecessor": {"node": "NODE-TEST"},
        "semantics": {
            "strength": "HARD",
            "blocking_stage": "START",
            "required_readiness": "R1",
        },
    }
    data[0]["cards"][seq[1]]["edges"] = [edge]
    data[0]["node_levels"]["NODE-TEST"] = ["R0", "R1"]
    qualify(data, seq[1])
    data[3]["candidates"][seq[1]]["dependencies"] = {}
    result = health(data)
    gap = result["candidates"][0]["hard_start_blockers"][0]
    assert gap["consumer_wp"] == seq[1]
    assert gap["dependency_id"] == "DEP-TEST"
    assert gap["required_readiness"] == "R1"
    assert "producer_wp" not in gap
    assert result["candidates"][0]["status"] == "WAITING_DEP"


def test_soft_and_later_stage_hard_do_not_block(baseline):
    data, seq = setup(baseline)
    data[0]["cards"][seq[1]]["edges"] = [
        {"id": "DEP-SOFT", "semantics": {"strength": "SOFT"}},
        {"id": "DEP-DONE", "semantics": {"strength": "HARD", "blocking_stage": "DONE"}},
    ]
    data[3]["candidates"][seq[1]] = {
        "result": "PASS",
        "dor": "PASS",
        "evidence_refs": ["comment:1"],
    }
    assert health(data)["prepared_next"] == seq[1]


@pytest.mark.parametrize("damage", ["source", "credential", "identity"])
def test_unavailable_sources_and_identity(baseline, damage):
    data, seq = setup(baseline)
    if damage == "source":
        data[3]["complete"] = False
    elif damage == "identity":
        data[2]["items"][seq[0]]["assignees"] = []
    else:
        data[3]["candidates"][seq[1]] = {"reason": "GITHUB_READ_UNAVAILABLE"}
    assert health(data)["health"] == "UNAVAILABLE"


def test_exhausted_backlog_healthy(baseline):
    data, seq = setup(baseline, False)
    for wp in seq:
        data[2]["items"][wp]["state"] = "DONE"
    assert health(data)["health"] == "HEALTHY"


def test_idle_eligible_backlog_never_healthy(baseline):
    data, seq = setup(baseline, False)
    qualify(data, seq[0])
    result = health(data)
    assert result["prepared_next"] == seq[0]
    assert result["health"] == "STALL_RISK"
    assert result["reasons"] == ["ELIGIBLE_WORK_AWAITS_GUARDED_RELEASE"]
