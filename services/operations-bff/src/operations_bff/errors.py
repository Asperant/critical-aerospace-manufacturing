"""Typed request failures that map one-to-one onto the v1 contract envelopes."""

from __future__ import annotations

from typing import Any


class BffError(Exception):
    """Failure with a fixed HTTP status and ErrorEnvelope category."""

    status: int
    category: str
    error_code: str
    retryable = False

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def envelope(self, correlation_id: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "error_code": self.error_code,
            "category": self.category,
            "message": self.message,
            "retryable": self.retryable,
            "correlation_id": correlation_id,
        }
        if self.details:
            body["details"] = self.details
        return body


class Unauthorized(BffError):
    """Missing, unknown, expired or invalidated session: 401, never data."""

    status = 401
    category = "UNAUTHORIZED"
    error_code = "SESSION_REQUIRED"


class Forbidden(BffError):
    """Authenticated request refused, e.g. a bad CSRF token: 403."""

    status = 403
    category = "FORBIDDEN"
    error_code = "CSRF_REJECTED"


class BadRequest(BffError):
    """Request breaks the contract: 400."""

    status = 400
    category = "VALIDATION_ERROR"
    error_code = "INVALID_REQUEST"


class AuthorityRejected(BadRequest):
    """Browser-supplied actor, role or identity authority: 400."""

    error_code = "BROWSER_AUTHORITY_REJECTED"


class LoginRejected(Unauthorized):
    """Login transaction or provider result refused: 401, no session created."""

    error_code = "LOGIN_REJECTED"


class Unavailable(BffError):
    """A required dependency such as the identity provider is down: 503."""

    status = 503
    category = "DEPENDENCY_UNAVAILABLE"
    error_code = "DEPENDENCY_UNAVAILABLE"
    retryable = True
