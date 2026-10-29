"""FastAPI transport adapter: HTTP only, no authentication logic of its own.

Wires getSession and logout from the v1 contract onto the session primitives,
and startLogin and completeLogin when a LoginService is supplied.
Queries and commands are not wired.
"""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import Lifespan

from .actor import Authenticated, authenticate_request, derive_actor_context
from .config import COOKIE_NAME, LOGIN_COOKIE_NAME, CookieSettings
from .errors import BadRequest, BffError
from .facility_state import FacilityStateQuery, FacilityStateService
from .login import LoginService
from .observability import (
    CORRELATION_HEADER,
    access_record,
    health_body,
    log_access,
    new_correlation_id,
)
from .overview import OverviewQuery, OverviewService
from .session import SessionManager, SessionRecord, session_view

Param = Annotated[str, Query(min_length=1, max_length=2048, pattern=r"\S")]
Ident = Annotated[str, Query(min_length=1, max_length=256, pattern=r"\S")]
OptIdent = Annotated[str | None, Query(min_length=1, max_length=256, pattern=r"\S")]
AsOf = Annotated[
    str | None,
    Query(
        pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z$"
    ),
]
Limit = Annotated[int, Query(ge=1, le=100)]
CursorParam = Annotated[str | None, Query(min_length=1, max_length=512, pattern=r"\S")]


def require_session(request: Request) -> Authenticated:
    """Dependency: runs before query validation, so anonymous callers get 401."""
    state = request.app.state
    return authenticate_request(
        state.sessions,
        method=request.method,
        cookies=request.cookies,
        headers=request.headers,
        now=state.clock(),
    )


Session = Annotated[Authenticated, Depends(require_session)]


def utc_now() -> datetime:
    return datetime.now(UTC)


def secure_cookies() -> bool:
    """HTTP cookies are disabled only by an explicit local demo setting."""
    return os.environ.get("OPERATIONS_BFF_COOKIE_SECURE", "1") != "0"


def correlation_id_of(request: Request) -> str:
    """The id the access middleware assigned to this request."""
    value = getattr(request.state, "correlation_id", None)
    return value if isinstance(value, str) else new_correlation_id()


def error_response(exc: BffError, correlation_id: str) -> JSONResponse:
    return JSONResponse(
        exc.envelope(correlation_id=correlation_id), status_code=exc.status
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
        secure=secure_cookies(),
        httponly=True,
        samesite=cookie.same_site,
    )


def clear_session_cookie(response: Response, cookie: CookieSettings) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=secure_cookies(),
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
    overview: OverviewService | None = None,
    facility_state: FacilityStateService | None = None,
) -> FastAPI:
    if not post_login_redirect.startswith("/") or post_login_redirect.startswith("//"):
        raise ValueError("post_login_redirect must be a same-origin absolute path")
    # The contract file is the only API description; no generated docs surface.
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    app.state.sessions = manager
    app.state.clock = clock

    @app.middleware("http")
    async def observe(  # pyright: ignore[reportUnusedFunction]
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = new_correlation_id()
        request.state.correlation_id = correlation_id
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[CORRELATION_HEADER] = correlation_id
            return response
        finally:
            route = request.scope.get("route")
            log_access(
                access_record(
                    method=request.method,
                    route=getattr(route, "path", None) or "unmatched",
                    operation_id=getattr(route, "operation_id", None),
                    status=status,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    correlation_id=correlation_id,
                )
            )

    @app.exception_handler(BffError)
    def bff_error(request: Request, exc: BffError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        return error_response(exc, correlation_id_of(request))

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, __: RequestValidationError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        # Never echo the rejected input back.
        return error_response(
            BadRequest("Request does not match the contract"),
            correlation_id_of(request),
        )

    @app.get("/healthz")
    def healthz() -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        # Operational surface, not part of the browser contract.
        return JSONResponse(
            health_body(
                login=login is not None,
                overview=overview is not None,
                facility_state=facility_state is not None,
            ),
            headers={"Cache-Control": "no-store"},
        )

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
    if overview is not None:
        _add_overview_route(app, overview, clock)
    if facility_state is not None:
        _add_facility_state_route(app, facility_state, clock)
    return app


def _add_overview_route(
    app: FastAPI, overview: OverviewService, clock: Callable[[], datetime]
) -> None:
    @app.get("/v1/overview", operation_id="getManufacturingOverview")
    def get_overview(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        auth: Session,
        world_id: Ident,
        simulation_run_id: OptIdent = None,
        branch_id: OptIdent = None,
        as_of: AsOf = None,
        limit: Limit = 50,
        cursor: CursorParam = None,
    ) -> JSONResponse:
        try:
            when = datetime.fromisoformat(as_of) if as_of else None
        except ValueError:
            raise BadRequest("as_of is not a valid instant") from None
        query = OverviewQuery(
            world_id=world_id,
            simulation_run_id=simulation_run_id,
            branch_id=branch_id,
            as_of=when,
            actor=derive_actor_context(auth.session, world_id),
            correlation_id=correlation_id_of(request),
        )
        body = overview.get(
            query,
            limit=limit,
            cursor=cursor,
            now=clock(),
            correlation_id=query.correlation_id,
        )
        return JSONResponse(body, headers={"Cache-Control": "no-store"})


def _add_facility_state_route(
    app: FastAPI, facility_state: FacilityStateService, clock: Callable[[], datetime]
) -> None:
    @app.get("/v1/facility-state", operation_id="getFacilityState")
    def get_facility_state(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        auth: Session,
        world_id: Ident,
        simulation_run_id: OptIdent = None,
        branch_id: OptIdent = None,
        as_of: AsOf = None,
    ) -> JSONResponse:
        try:
            when = datetime.fromisoformat(as_of) if as_of else None
        except ValueError:
            raise BadRequest("as_of is not a valid instant") from None
        query = FacilityStateQuery(
            world_id=world_id,
            simulation_run_id=simulation_run_id,
            branch_id=branch_id,
            as_of=when,
            actor=derive_actor_context(auth.session, world_id),
            correlation_id=correlation_id_of(request),
        )
        body = facility_state.get(
            query,
            now=clock(),
            correlation_id=query.correlation_id,
        )
        return JSONResponse(body, headers={"Cache-Control": "no-store"})


def _clear_login_cookie(response: Response, cookie: CookieSettings) -> None:
    response.delete_cookie(
        key=LOGIN_COOKIE_NAME,
        path="/v1/session",
        secure=secure_cookies(),
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
            secure=secure_cookies(),
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
            failure = error_response(exc, correlation_id_of(request))
            _clear_login_cookie(failure, cookie)
            return failure
        response = Response(
            status_code=302,
            headers={"Location": landing, "Cache-Control": "no-store"},
        )
        write_session_cookie(response, record, cookie, now)
        _clear_login_cookie(response, cookie)
        return response
