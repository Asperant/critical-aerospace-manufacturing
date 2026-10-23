"""FastAPI transport adapter: HTTP only, no authentication logic of its own.

Wires getSession and logout from the v1 contract onto the session primitives,
and startLogin and completeLogin when a LoginService is supplied.
Queries and commands are not wired.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import Lifespan

from .actor import Authenticated, authenticate_request
from .config import COOKIE_NAME, LOGIN_COOKIE_NAME, CookieSettings
from .errors import BadRequest, BffError
from .login import LoginService
from .session import SessionManager, SessionRecord, session_view

Param = Annotated[str, Query(min_length=1, max_length=2048, pattern=r"\S")]


def utc_now() -> datetime:
    return datetime.now(UTC)


def error_response(exc: BffError) -> JSONResponse:
    return JSONResponse(
        exc.envelope(correlation_id=uuid.uuid4().hex), status_code=exc.status
    )


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
    login: LoginService | None = None,
    post_login_redirect: str = "/",
    lifespan: Lifespan[FastAPI] | None = None,
) -> FastAPI:
    if not post_login_redirect.startswith("/") or post_login_redirect.startswith("//"):
        raise ValueError("post_login_redirect must be a same-origin absolute path")
    # The contract file is the only API description; no generated docs surface.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.exception_handler(BffError)
    def bff_error(_: Request, exc: BffError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    def invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        # Never echo the rejected input back.
        return error_response(BadRequest("Request does not match the contract"))

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

    if login is not None:
        _add_login_routes(app, login, cookie, clock, post_login_redirect)
    return app


def _clear_login_cookie(response: Response) -> None:
    response.delete_cookie(
        key=LOGIN_COOKIE_NAME,
        path="/v1/session",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _add_login_routes(
    app: FastAPI,
    login: LoginService,
    cookie: CookieSettings,
    clock: Callable[[], datetime],
    landing: str,
) -> None:
    @app.get("/v1/session/login", operation_id="startLogin", status_code=302)
    def start_login() -> Response:  # pyright: ignore[reportUnusedFunction]
        started = login.start(clock())
        response = Response(
            status_code=302,
            headers={"Location": started.location, "Cache-Control": "no-store"},
        )
        # Lax so the cookie survives the provider's top-level redirect back.
        response.set_cookie(
            key=LOGIN_COOKIE_NAME,
            value=started.binding,
            max_age=started.max_age_seconds,
            path="/v1/session",
            secure=True,
            httponly=True,
            samesite="lax",
        )
        return response

    @app.get("/v1/session/callback", operation_id="completeLogin", status_code=302)
    def complete_login(request: Request, code: Param, state: Param) -> Response:  # pyright: ignore[reportUnusedFunction]
        now = clock()
        try:
            record = login.complete(
                code=code,
                state=state,
                binding=request.cookies.get(LOGIN_COOKIE_NAME),
                previous_session_id=request.cookies.get(COOKIE_NAME),
                now=now,
            )
        except BffError as exc:
            # The transaction is spent whatever the outcome; drop its cookie.
            failure = error_response(exc)
            _clear_login_cookie(failure)
            return failure
        response = Response(
            status_code=302,
            headers={"Location": landing, "Cache-Control": "no-store"},
        )
        write_session_cookie(response, record, cookie, now)
        _clear_login_cookie(response)
        return response
