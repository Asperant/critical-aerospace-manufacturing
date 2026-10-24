"""WP-SEC-003 slice 2: Core authorization enforcement mechanism.

Wraps a protected handler so the slice 1 deny-by-default policy is evaluated
before the handler can run. A denial raises ``AuthorizationDenied`` and the
handler is never invoked; any fault while evaluating also denies.

``EnforcementRegistry`` records which catalogued protected actions have an
enforcement binding, so an entrypoint without one is detectable. No Core command
handler exists yet and none is created here; the registry starts empty and the
real handlers bind themselves when they are written. This module resolves no
roles to permissions, reads no identity or configuration, and is not an HTTP,
IdP or Automation enforcement point.
"""

from collections.abc import Callable, Collection, Mapping
from functools import wraps
from types import MappingProxyType
from typing import Concatenate, ParamSpec, TypeVar

from .authz import PROTECTED_ACTIONS, Decision, evaluate

P = ParamSpec("P")
R = TypeVar("R")


class AuthorizationDenied(PermissionError):
    """The caller lacks the exact permission for the protected action.

    The message carries neither the action text nor any permission; ``action``
    holds the requested action only when it is a string.
    """

    def __init__(self, action: object) -> None:
        super().__init__("authorization denied")
        self.action: str | None = action if isinstance(action, str) else None


class ProtectedBindingError(ValueError):
    """An enforcement binding is invalid: unknown action or a duplicate binding."""


class UnboundProtectedActions(ProtectedBindingError):
    """Catalogued protected actions exist without an enforcement binding."""

    def __init__(self, actions: tuple[str, ...]) -> None:
        super().__init__("unbound protected actions: " + ", ".join(actions))
        self.actions = actions


def authorize(principal_permissions: Collection[str] | None, action: str) -> None:
    """Return only when the policy allows; otherwise raise ``AuthorizationDenied``."""
    try:
        decision = evaluate(principal_permissions, action)
    except Exception:  # an evaluation fault is a denial, never an allow
        decision = Decision.DENY
    if decision is not Decision.ALLOW:
        raise AuthorizationDenied(action)


def enforce(
    principal_permissions: Collection[str] | None,
    action: str,
    handler: Callable[P, R],
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Authorize first, then call ``handler`` exactly once; never call it on DENY."""
    authorize(principal_permissions, action)
    return handler(*args, **kwargs)


def _reference(handler: Callable[..., object]) -> str:
    """Module-qualified name of a function, or of the type of a callable object."""
    owner = handler if hasattr(handler, "__qualname__") else type(handler)
    return f"{owner.__module__}.{owner.__qualname__}"


class EnforcementRegistry:
    """Tracks which catalogued protected actions have an enforcement binding."""

    def __init__(self) -> None:
        self._bindings: dict[str, str] = {}

    def bind(
        self, action: str
    ) -> Callable[
        [Callable[P, R]], Callable[Concatenate[Collection[str] | None, P], R]
    ]:
        """Decorator factory: the guarded handler takes the permissions first."""
        if action not in PROTECTED_ACTIONS:
            raise ProtectedBindingError("unknown protected action")

        def decorate(
            handler: Callable[P, R],
        ) -> Callable[Concatenate[Collection[str] | None, P], R]:
            if action in self._bindings:
                raise ProtectedBindingError("protected action already bound")
            self._bindings[action] = _reference(handler)

            @wraps(handler)
            def guarded(
                principal_permissions: Collection[str] | None,
                /,
                *args: P.args,
                **kwargs: P.kwargs,
            ) -> R:
                return enforce(principal_permissions, action, handler, *args, **kwargs)

            return guarded

        return decorate

    def bound_actions(self) -> Mapping[str, str]:
        """Action id to the bound handler's module-qualified name (read-only copy)."""
        return MappingProxyType(dict(self._bindings))

    def unbound_actions(self) -> tuple[str, ...]:
        """Catalogued protected actions with no binding, sorted."""
        return tuple(sorted(set(PROTECTED_ACTIONS) - set(self._bindings)))

    def assert_fully_bound(self) -> None:
        """Raise ``UnboundProtectedActions`` unless every catalogued action is bound."""
        unbound = self.unbound_actions()
        if unbound:
            raise UnboundProtectedActions(unbound)
