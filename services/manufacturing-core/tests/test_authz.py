"""TEST-SEC-AUTHZ-NEG unit subset: deny-by-default Core authorization policy.

Pure, isolated evidence only. This is not the integrated negative suite, and
claims neither AV-SCEN-04 nor BENCH-RQ3-001.
"""

import pytest
from manufacturing_core.authz import PROTECTED_ACTIONS, Decision, evaluate

ACTIONS = sorted(PROTECTED_ACTIONS)
CANDIDATE_MEMBERS = {
    "PlaceLotOnHold",
    "ReleaseMaterialHold",
    "IsolateMachine",
    "ReleaseMachineIsolation",
    "ActivateSchedule",
    "CreateMaintenanceWorkOrder",
    "UpdateLotPriority",
    "ExecuteApprovedReworkDirective",
}


def test_catalog_is_the_closed_candidate_action_set() -> None:
    assert set(PROTECTED_ACTIONS) == CANDIDATE_MEMBERS


def test_catalog_entries_are_complete_and_unambiguous() -> None:
    entries = list(PROTECTED_ACTIONS.values())
    for entry in entries:
        assert PROTECTED_ACTIONS[entry.action_id] is entry
        assert entry.required_permission.strip() == entry.required_permission
        assert entry.core_entrypoint.startswith("manufacturing_core.commands.")
    for field in ("required_permission", "core_entrypoint"):
        values = [getattr(entry, field) for entry in entries]
        assert len(set(values)) == len(values)


def test_catalog_is_read_only() -> None:
    with pytest.raises(TypeError):
        PROTECTED_ACTIONS["Unlisted"] = PROTECTED_ACTIONS["IsolateMachine"]  # type: ignore[index]
    with pytest.raises(TypeError):
        del PROTECTED_ACTIONS["IsolateMachine"]  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        PROTECTED_ACTIONS["IsolateMachine"].required_permission = "x"  # type: ignore[misc]


@pytest.mark.parametrize("action", ACTIONS)
def test_exact_required_permission_allows(action: str) -> None:
    permission = PROTECTED_ACTIONS[action].required_permission
    assert evaluate({permission}, action) is Decision.ALLOW
    assert evaluate([permission, "unrelated"], action) is Decision.ALLOW
    assert evaluate((permission,), action) is Decision.ALLOW
    assert evaluate(frozenset({permission}), action) is Decision.ALLOW


@pytest.mark.parametrize("action", ACTIONS)
def test_known_action_without_required_permission_denies(action: str) -> None:
    assert evaluate(set(), action) is Decision.DENY
    assert evaluate(["unrelated.permission"], action) is Decision.DENY


@pytest.mark.parametrize("action", ACTIONS)
def test_every_other_actions_permission_denies(action: str) -> None:
    others = {
        entry.required_permission
        for name, entry in PROTECTED_ACTIONS.items()
        if name != action
    }
    assert evaluate(others, action) is Decision.DENY


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("variant", ["upper", "padded", "prefix", "suffix", "wildcard"])
def test_inexact_permission_denies(action: str, variant: str) -> None:
    permission = PROTECTED_ACTIONS[action].required_permission
    inexact = {
        "upper": permission.upper(),
        "padded": f" {permission} ",
        "prefix": f"x{permission}",
        "suffix": f"{permission}.extra",
        "wildcard": "*",
    }[variant]
    assert evaluate({inexact, "core.*", "admin"}, action) is Decision.DENY


@pytest.mark.parametrize(
    "action",
    ["", " ", "Unknown", "isolatemachine", "ISOLATEMACHINE", " IsolateMachine", "*"],
)
def test_unknown_action_denies_even_with_every_known_permission(action: str) -> None:
    every = {entry.required_permission for entry in PROTECTED_ACTIONS.values()}
    assert evaluate(every | {action}, action) is Decision.DENY


@pytest.mark.parametrize("action", [None, 1, b"IsolateMachine", ["IsolateMachine"]])
def test_non_string_action_denies(action: object) -> None:
    every = {entry.required_permission for entry in PROTECTED_ACTIONS.values()}
    assert evaluate(every, action) is Decision.DENY  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "permissions",
    [
        None,
        "core.machine.isolate",
        b"core.machine.isolate",
        bytearray(b"core.machine.isolate"),
        7,
        object(),
        iter(["core.machine.isolate"]),
    ],
)
def test_missing_or_malformed_permission_collection_denies(
    permissions: object,
) -> None:
    assert evaluate(permissions, "IsolateMachine") is Decision.DENY  # type: ignore[arg-type]


def test_non_string_members_do_not_satisfy_the_requirement() -> None:
    hostile: list[object] = [None, 1, b"core.machine.isolate"]
    assert evaluate(hostile, "IsolateMachine") is Decision.DENY  # type: ignore[arg-type]
    hostile.append("core.machine.isolate")
    assert evaluate(hostile, "IsolateMachine") is Decision.ALLOW  # type: ignore[arg-type]


def test_evaluation_is_pure() -> None:
    permissions = {"core.machine.isolate"}
    before = set(permissions)
    assert evaluate(permissions, "IsolateMachine") is Decision.ALLOW
    assert evaluate(permissions, "IsolateMachine") is Decision.ALLOW
    assert permissions == before
