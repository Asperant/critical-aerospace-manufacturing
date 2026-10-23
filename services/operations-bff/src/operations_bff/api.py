"""FastAPI transport adapter: HTTP only, no authentication logic of its own.

Wires getSession and logout from the v1 contract onto the session primitives.
Login, callback, queries and commands are not wired.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .actor import Authenticated, authenticate_request
from .config import COOKIE_NAME, CookieSettings
from .errors import BffError
from .session import SessionManager, SessionRecord, session_view


def utc_now() -> datetime:
    return datetime.now(UTC)


def write_session_cookie(
    response: Response, record: SessionRecord, cookie: CookieSettings, now: datetime
) -> None:
    """Set the opaque session cookie; lifetime is the session's remaining life."""
    remaining = max(0, int((record.expires_at - now).total_seconds()))
    response.set_cookie(
        key=COOKIE_NAME,
        value=record.session_id,
        max_age=remaining,
        path="/",
        secure=True,
        httponly=True,
        samesite=cookie.same_site,
    )


def clear_session_cookie(response: Response, cookie: CookieSettings) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite=cookie.same_site,
    )


def create_app(
    manager: SessionManager,
    *,
    cookie: CookieSettings,
    clock: Callable[[], datetime] = utc_now,
) -> FastAPI:
    # The contract file is the only API description; no generated docs surface.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(BffError)
    def bff_error(_: Request, exc: BffError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        body = exc.envelope(correlation_id=uuid.uuid4().hex)
        return JSONResponse(body, status_code=exc.status)

    def authenticate(request: Request) -> Authenticated:
        return authenticate_request(
            manager,
            method=request.method,
            cookies=request.cookies,
            headers=request.headers,
            now=clock(),
        )

    @app.get("/v1/session", operation_id="getSession")
    def get_session(request: Request) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        auth = authenticate(request)
        return JSONResponse(
            session_view(auth.session), headers={"Cache-Control": "no-store"}
        )

    @app.post("/v1/session/logout", operation_id="logout", status_code=204)
    def logout(request: Request) -> Response:  # pyright: ignore[reportUnusedFunction]
        auth = authenticate(request)
        manager.invalidate(auth.session.session_id)
        response = Response(status_code=204, headers={"Cache-Control": "no-store"})
        clear_session_cookie(response, cookie)
        return response

    return app
