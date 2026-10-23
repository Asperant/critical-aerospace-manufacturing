"""Session, CSRF and ActorContext primitives against the Slice 2 contract."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError
from operations_bff.actor import (
    authenticate_request,
    reject_browser_authority,
)
from operations_bff.config import COOKIE_NAME, CSRF_HEADER, SessionConfig
from operations_bff.errors import BadRequest, BffError, Forbidden, Unauthorized
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
    SessionRecord,
    session_view,
)
from test_contract_v1 import BASE, load_json, openapi, registry, validator_for

T0 = datetime(2026, 10, 23, 8, 0, 0, tzinfo=UTC)
IDENTITY = AuthenticatedIdentity(
    subject="U-SYNTHETIC-01",
    display_name="Synthetic Operator",
    roles=("ops-controller",),
    environment_id="ENV-SYNTHETIC-TEST",
)


def manager(config: SessionConfig | None = None) -> SessionManager:
    return SessionManager(InMemorySessionStore(), config)


def request(
    mgr: SessionManager,
    record: SessionRecord | None,
    *,
    method: str = "GET",
    csrf: str | None = None,
    now: datetime = T0,
    headers: dict[str, str] | None = None,
    world_id: str | None = "W-SYNTHETIC-TEST",
):
    cookies = {COOKIE_NAME: record.session_id} if record else {}
    sent = dict(headers or {})
    if csrf is not None:
        sent[CSRF_HEADER] = csrf
    return authenticate_request(
        mgr, method=method, cookies=cookies, headers=sent, now=now, world_id=world_id
    )


def envelope_validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": BASE + f"common.schema.json#/$defs/{name}"}, registry=registry()
    )


def test_valid_session_derives_actor_context_from_session_only() -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    auth = request(mgr, record, now=T0 + timedelta(minutes=1))
    assert auth.actor.actor_id == "U-SYNTHETIC-01"
    assert auth.actor.roles == ("ops-controller",)
    assert auth.actor.environment_id == "ENV-SYNTHETIC-TEST"
    assert auth.actor.world_id == "W-SYNTHETIC-TEST"
    assert auth.actor.derived_from == "SESSION"


@pytest.mark.parametrize("case", ["missing", "unknown", "expired_idle", "expired_abs"])
def test_missing_or_expired_session_is_401(case: str) -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    when = T0
    cookies: dict[str, str] = {COOKIE_NAME: record.session_id}
    if case == "missing":
        cookies = {}
    elif case == "unknown":
        cookies = {COOKIE_NAME: "not-a-session"}
    elif case == "expired_idle":
        when = T0 + mgr.config.idle_ttl
    else:
        # Keep the session active, then pass the absolute deadline.
        step = mgr.config.idle_ttl / 2
        moment = T0
        while moment + step < record.expires_at:
            moment += step
            mgr.resolve(record.session_id, moment)
        when = record.expires_at
    with pytest.raises(Unauthorized) as caught:
        authenticate_request(mgr, method="GET", cookies=cookies, headers={}, now=when)
    assert caught.value.status == 401
    envelope_validator("UnauthorizedError").validate(caught.value.envelope("C-1"))


def test_anonymous_post_is_401_not_403() -> None:
    mgr = manager()
    with pytest.raises(Unauthorized):
        request(mgr, None, method="POST", csrf="anything")


@pytest.mark.parametrize("csrf", [None, "", "wrong-token"])
@pytest.mark.parametrize("method", ["POST", "put", "PATCH", "DELETE"])
def test_bad_or_missing_csrf_on_state_change_is_403(
    csrf: str | None, method: str
) -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    with pytest.raises(Forbidden) as caught:
        request(mgr, record, method=method, csrf=csrf)
    assert caught.value.status == 403
    envelope_validator("ForbiddenError").validate(caught.value.envelope("C-2"))


def test_csrf_is_enforced_per_session_and_not_needed_for_reads() -> None:
    mgr = manager()
    first = mgr.create(IDENTITY, T0)
    second = mgr.create(IDENTITY, T0)
    assert request(mgr, first, method="GET").actor.actor_id == IDENTITY.subject
    assert request(mgr, first, method="POST", csrf=first.csrf_token)
    with pytest.raises(Forbidden):
        request(mgr, first, method="POST", csrf=second.csrf_token)


def test_actor_injection_cannot_override_session_actor() -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    for header in ("X-Actor", "x-user-id", "X-Roles"):
        with pytest.raises(BadRequest):
            request(mgr, record, headers={header: "U-ADMIN"})
    for payload in (
        {"actor_id": "U-ADMIN"},
        {"nested": {"Roles": ["admin"]}},
        {"items": [{"permissions": ["all"]}]},
        {"session": "x"},
    ):
        with pytest.raises(BadRequest) as caught:
            reject_browser_authority(payload)
        assert caught.value.status == 400
        envelope_validator("ErrorEnvelope").validate(caught.value.envelope("C-3"))
    reject_browser_authority({"reason": "vibration", "limits": [{"max": 3}]})
    # Whatever the browser sends, the context still comes from the session.
    auth = request(mgr, record, world_id="W-SYNTHETIC-TEST")
    assert auth.actor.actor_id == IDENTITY.subject


def test_rejected_keys_match_the_contract_parameter_guard() -> None:
    """The runtime guard and the schema guard refuse the same command keys."""
    validator = validator_for("command.schema.json#/$defs/ParameterObject")
    for key in ("actor_id", "User", "ROLES", "permission", "principal", "csrf_x"):
        with pytest.raises(ValidationError):
            validator.validate({key: 1})
        with pytest.raises(BadRequest):
            reject_browser_authority({key: 1})
    for key in ("reason", "limits", "target_state"):
        validator.validate({key: 1})
        reject_browser_authority({key: 1})


def test_session_rotation_replaces_id_and_never_extends_expiry() -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    later = T0 + mgr.config.rotate_after
    assert mgr.needs_rotation(record, later)
    assert not mgr.needs_rotation(record, T0 + timedelta(minutes=1))
    rotated = mgr.rotate(record.session_id, later)
    assert rotated.session_id != record.session_id
    assert rotated.csrf_token != record.csrf_token
    assert rotated.expires_at == record.expires_at
    assert rotated.authenticated_at == record.authenticated_at
    with pytest.raises(Unauthorized):
        mgr.resolve(record.session_id, later)
    assert mgr.resolve(rotated.session_id, later).identity == IDENTITY


def test_login_rotates_and_ends_a_previous_session() -> None:
    mgr = manager()
    old = mgr.create(IDENTITY, T0)
    new = mgr.create(IDENTITY, T0, previous_session_id=old.session_id)
    assert new.session_id != old.session_id
    with pytest.raises(Unauthorized):
        mgr.resolve(old.session_id, T0)


def test_logout_invalidates_server_side() -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    mgr.invalidate(record.session_id)
    with pytest.raises(Unauthorized):
        mgr.resolve(record.session_id, T0)


def test_absolute_expiry_bound_and_config_limits() -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    assert record.expires_at - T0 == mgr.config.absolute_ttl
    assert mgr.config.absolute_ttl <= timedelta(hours=12)
    for bad in (
        {"absolute_ttl": timedelta(hours=13)},
        {"absolute_ttl": timedelta(0)},
        {"idle_ttl": timedelta(hours=9)},
        {"rotate_after": timedelta(hours=1)},
        {"idle_ttl": timedelta(0)},
    ):
        with pytest.raises(ValueError):
            SessionConfig(**bad)


def test_store_never_holds_a_usable_cookie_value() -> None:
    store = InMemorySessionStore()
    record = SessionManager(store).create(IDENTITY, T0)
    keys: Any = list(store._records)  # pyright: ignore[reportPrivateUsage]
    assert record.session_id not in keys
    assert all(len(key) == 64 for key in keys)


def test_no_browser_visible_bearer_access_or_refresh_token() -> None:
    mgr = manager()
    record = mgr.create(IDENTITY, T0)
    view = session_view(record)
    validator_for("session.schema.json").validate(view)
    assert view["csrf_token"] == record.csrf_token
    assert view["actor"]["derived_from"] == "SESSION"
    assert "session_id" not in view
    banned = ("access", "refresh", "bearer", "jwt", "id_token", "password", "secret")

    def keys(node: Any) -> list[str]:
        if isinstance(node, dict):
            found: list[str] = []
            for name, item in node.items():  # pyright: ignore[reportUnknownVariableType]
                found.append(str(name))  # pyright: ignore[reportUnknownArgumentType]
                found.extend(keys(item))
            return found
        return []

    assert not [k for k in keys(view) if any(b in k.lower() for b in banned)]
    # The identity handed over by the future OIDC adapter has no token fields.
    names = {f.name for f in dataclasses.fields(AuthenticatedIdentity)}
    assert not [n for n in names if any(b in n for b in banned)]


def test_session_view_matches_contract_fixture_shape() -> None:
    fixture = load_json("session.normal.json")
    mgr = manager()
    record = mgr.create(IDENTITY, datetime(2026, 10, 23, 8, 0, 0, tzinfo=UTC))
    view = session_view(record)
    assert set(view) == set(fixture)
    assert view["authenticated_at"] == fixture["authenticated_at"]
    assert view["expires_at"] == "2026-10-23T16:00:00Z" == fixture["expires_at"]
    assert view["actor"] == fixture["actor"]


def test_runtime_names_match_the_openapi_security_schemes() -> None:
    schemes = openapi()["components"]["securitySchemes"]
    assert schemes["browserSession"]["name"] == COOKIE_NAME
    assert schemes["csrfToken"]["name"] == CSRF_HEADER


def test_errors_are_one_hierarchy_with_fixed_statuses() -> None:
    assert (Unauthorized.status, Forbidden.status, BadRequest.status) == (401, 403, 400)
    assert issubclass(Unauthorized, BffError)
