"""TEST-SEC-003-001 unit subset: Core authorization enforcement mechanism.

Uses local test handlers only; no Core command handler exists or is simulated.
This is not the integrated negative suite and claims neither AV-SCEN-04 nor
BENCH-RQ3-001.
"""

from collections.abc import Iterator

import pytest
from manufacturing_core.authz import PROTECTED_ACTIONS
from manufacturing_core.enforcement import (
    AuthorizationDenied,
    EnforcementRegistry,
    ProtectedBindingError,
    UnboundProtectedActions,
    authorize,
    enforce,
)

ACTIONS = sorted(PROTECTED_ACTIONS)


class Handler:
    """Counts invocations and records the arguments it was given."""

    def __init__(self, result: object = "done") -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.result = result

    def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls.append((args, kwargs))
        return self.result


class ExplodingPermissions:
    """A collection whose iteration fails; a fault must deny, not allow."""

    def __len__(self) -> int:
        return 1

    def __contains__(self, item: object) -> bool:
        raise RuntimeError("boom")

    def __iter__(self) -> Iterator[str]:
        raise RuntimeError("boom")


def permission(action: str) -> str:
    return PROTECTED_ACTIONS[action].required_permission


@pytest.mark.parametrize("context", [None, set(), [], (), frozenset()])
@pytest.mark.parametrize("action", ACTIONS)
def test_missing_context_denies_without_invoking(context: object, action: str) -> None:
    handler = Handler()
    with pytest.raises(AuthorizationDenied):
        enforce(context, action, handler)  # type: ignore[arg-type]
    assert handler.calls == []


@pytest.mark.parametrize("action", ["", "Unknown", "isolatemachine", " IsolateMachine"])
def test_unknown_action_denies_even_with_every_permission(action: str) -> None:
    every = {entry.required_permission for entry in PROTECTED_ACTIONS.values()}
    handler = Handler()
    with pytest.raises(AuthorizationDenied) as caught:
        enforce(every, action, handler)
    assert caught.value.action == action
    assert handler.calls == []


@pytest.mark.parametrize("action", [None, 1, b"IsolateMachine", ["IsolateMachine"]])
def test_non_string_action_denies_without_invoking(action: object) -> None:
    every = {entry.required_permission for entry in PROTECTED_ACTIONS.values()}
    handler = Handler()
    with pytest.raises(AuthorizationDenied) as caught:
        enforce(every, action, handler)  # type: ignore[arg-type]
    assert caught.value.action is None
    assert handler.calls == []


@pytest.mark.parametrize("action", ACTIONS)
def test_wrong_or_missing_permission_denies_without_invoking(action: str) -> None:
    others = {
        entry.required_permission
        for name, entry in PROTECTED_ACTIONS.items()
        if name != action
    }
    handler = Handler()
    for context in (others, ["unrelated"], {permission(action).upper()}, {"*"}):
        with pytest.raises(AuthorizationDenied):
            enforce(context, action, handler)
    assert handler.calls == []


@pytest.mark.parametrize("action", ACTIONS)
def test_exact_permission_invokes_handler_exactly_once(action: str) -> None:
    handler = Handler(result=42)
    result = enforce({permission(action)}, action, handler, "a", key="b")
    assert result == 42
    assert handler.calls == [(("a",), {"key": "b"})]


@pytest.mark.parametrize(
    "context", [ExplodingPermissions(), "core.machine.isolate", b"core.machine.isolate"]
)
def test_evaluation_fault_or_malformed_context_denies(context: object) -> None:
    handler = Handler()
    with pytest.raises(AuthorizationDenied):
        enforce(context, "IsolateMachine", handler)  # type: ignore[arg-type]
    assert handler.calls == []


def test_denied_call_never_reaches_a_non_callable_handler() -> None:
    with pytest.raises(AuthorizationDenied):
        enforce(set(), "IsolateMachine", None)  # type: ignore[arg-type]


def test_handler_errors_propagate_unchanged_after_one_call() -> None:
    calls: list[int] = []

    def failing() -> None:
        calls.append(1)
        raise ValueError("handler failure")

    with pytest.raises(ValueError, match="handler failure"):
        enforce({permission("IsolateMachine")}, "IsolateMachine", failing)
    assert calls == [1]


def test_denial_message_discloses_no_permission_or_action_text() -> None:
    secret = "core.machine.isolate-secret-variant"
    with pytest.raises(AuthorizationDenied) as caught:
        authorize({secret}, "IsolateMachine")
    assert secret not in str(caught.value)
    assert "IsolateMachine" not in str(caught.value)
    assert isinstance(caught.value, PermissionError)


def test_authorize_allows_only_the_exact_permission() -> None:
    authorize({permission("PlaceLotOnHold")}, "PlaceLotOnHold")
    with pytest.raises(AuthorizationDenied):
        authorize({permission("PlaceLotOnHold")}, "ReleaseMaterialHold")


def test_registry_starts_with_every_catalogued_action_unbound() -> None:
    registry = EnforcementRegistry()
    assert registry.unbound_actions() == tuple(ACTIONS)
    assert dict(registry.bound_actions()) == {}
    with pytest.raises(UnboundProtectedActions) as caught:
        registry.assert_fully_bound()
    assert caught.value.actions == tuple(ACTIONS)


def test_unguarded_catalog_entry_is_detected() -> None:
    registry = EnforcementRegistry()
    for action in ACTIONS[:-1]:
        registry.bind(action)(Handler())
    assert registry.unbound_actions() == (ACTIONS[-1],)
    with pytest.raises(UnboundProtectedActions, match=ACTIONS[-1]):
        registry.assert_fully_bound()
    registry.bind(ACTIONS[-1])(Handler())
    assert registry.unbound_actions() == ()
    registry.assert_fully_bound()


def test_bound_handler_enforces_before_calling() -> None:
    registry = EnforcementRegistry()
    handler = Handler(result="ok")

    @registry.bind("IsolateMachine")
    def isolate(machine_id: str) -> object:
        return handler(machine_id)

    assert registry.bound_actions()["IsolateMachine"].endswith(
        "test_bound_handler_enforces_before_calling.<locals>.isolate"
    )
    for context in (None, set(), {"core.lot.place_hold"}):
        with pytest.raises(AuthorizationDenied):
            isolate(context, "CNC-1")  # type: ignore[arg-type]
    assert handler.calls == []
    assert isolate({permission("IsolateMachine")}, "CNC-1") == "ok"
    assert handler.calls == [(("CNC-1",), {})]


def test_binding_is_fail_closed_for_unknown_and_duplicate_actions() -> None:
    registry = EnforcementRegistry()
    with pytest.raises(ProtectedBindingError):
        registry.bind("NotCatalogued")
    registry.bind("IsolateMachine")(Handler())
    with pytest.raises(ProtectedBindingError):
        registry.bind("IsolateMachine")(Handler())
    assert registry.unbound_actions() == tuple(
        a for a in ACTIONS if a != "IsolateMachine"
    )


def test_registries_are_independent_and_bound_view_is_read_only() -> None:
    first, second = EnforcementRegistry(), EnforcementRegistry()
    first.bind("IsolateMachine")(Handler())
    assert "IsolateMachine" in first.bound_actions()
    assert second.unbound_actions() == tuple(ACTIONS)
    with pytest.raises(TypeError):
        first.bound_actions()["Other"] = "x"  # type: ignore[index]
