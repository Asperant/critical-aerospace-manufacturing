"""Typed request failures that map one-to-one onto the v1 contract envelopes."""

from __future__ import annotations

from typing import Any


class BffError(Exception):
    """Failure with a fixed HTTP status and ErrorEnvelope category."""

    status: int
    category: str
    error_code: str
    retryable = False

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def envelope(self, correlation_id: str) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "category": self.category,
            "message": self.message,
            "retryable": self.retryable,
            "correlation_id": correlation_id,
        }


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
    """Request breaks the contract, e.g. browser-supplied actor authority: 400."""

    status = 400
    category = "VALIDATION_ERROR"
    error_code = "BROWSER_AUTHORITY_REJECTED"
