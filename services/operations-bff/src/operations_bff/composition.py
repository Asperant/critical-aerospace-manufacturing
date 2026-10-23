"""Composition root: reads runtime settings and wires the existing parts.

No behaviour lives here. Required configuration has no default, so a missing
or invalid value stops start-up with a message naming the setting. The stores
are in memory, so one process serves all sessions; a shared store is a later
decision.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, cast

import httpx
from fastapi import FastAPI

from .api import create_app, utc_now
from .config import CookieSettings, LoginConfig, SessionConfig
from .login import InMemoryLoginStore, LoginService
from .oidc import OidcIdentityProvider, OidcSettings
from .session import InMemorySessionStore, SessionManager

PREFIX = "OPERATIONS_BFF_"
SAME_SITE = PREFIX + "COOKIE_SAMESITE"
SESSION_ABSOLUTE = PREFIX + "SESSION_ABSOLUTE_TTL_SECONDS"
SESSION_IDLE = PREFIX + "SESSION_IDLE_TTL_SECONDS"
SESSION_ROTATE = PREFIX + "SESSION_ROTATE_AFTER_SECONDS"
LOGIN_TTL = PREFIX + "LOGIN_TTL_SECONDS"
LOGIN_MAX_PENDING = PREFIX + "LOGIN_MAX_PENDING"
POST_LOGIN_PATH = PREFIX + "POST_LOGIN_PATH"


class ConfigurationError(ValueError):
    """Start-up configuration is missing or invalid; lists every problem."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("invalid configuration: " + "; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class RuntimeSettings:
    oidc: OidcSettings
    cookie: CookieSettings
    session: SessionConfig
    login: LoginConfig
    post_login_path: str

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> RuntimeSettings:
        problems: list[str] = []

        def text(name: str) -> str | None:
            value = environ.get(name, "").strip()
            return value or None

        def seconds(name: str, required: bool) -> timedelta | None:
            raw = text(name)
            if raw is None:
                if required:
                    problems.append(f"{name} is required")
                return None
            if not raw.isdecimal() or int(raw) <= 0:
                problems.append(f"{name} must be a positive whole number of seconds")
                return None
            return timedelta(seconds=int(raw))

        same_site = text(SAME_SITE)
        if same_site is None:
            problems.append(f"{SAME_SITE} is required (strict or lax)")
        elif same_site not in ("strict", "lax"):
            problems.append(f"{SAME_SITE} must be strict or lax")
        absolute = seconds(SESSION_ABSOLUTE, True)
        idle = seconds(SESSION_IDLE, True)
        rotate = seconds(SESSION_ROTATE, True)
        login_ttl = seconds(LOGIN_TTL, False)
        pending_raw = text(LOGIN_MAX_PENDING)
        pending: int | None = None
        if pending_raw is not None:
            if pending_raw.isdecimal() and int(pending_raw) >= 1:
                pending = int(pending_raw)
            else:
                problems.append(f"{LOGIN_MAX_PENDING} must be a positive whole number")
        oidc: OidcSettings | None = None
        try:
            oidc = OidcSettings.from_environ(environ)
        except ValueError as exc:
            problems.append(str(exc))
        session: SessionConfig | None = None
        if absolute and idle and rotate:
            try:
                session = SessionConfig(absolute, idle, rotate)
            except ValueError as exc:
                problems.append(str(exc))
        login_defaults = LoginConfig()
        login: LoginConfig | None = None
        try:
            login = LoginConfig(
                ttl=login_ttl or login_defaults.ttl,
                max_pending=pending or login_defaults.max_pending,
            )
        except ValueError as exc:
            problems.append(str(exc))
        post_login = text(POST_LOGIN_PATH) or "/"
        if not post_login.startswith("/") or post_login.startswith("//"):
            problems.append(f"{POST_LOGIN_PATH} must be a same-origin absolute path")
        if problems or oidc is None or session is None or login is None:
            raise ConfigurationError(problems)
        return cls(
            oidc=oidc,
            cookie=CookieSettings(same_site=cast(Literal["strict", "lax"], same_site)),
            session=session,
            login=login,
            post_login_path=post_login,
        )


def build_app(
    settings: RuntimeSettings,
    *,
    http_client: httpx.Client | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> FastAPI:
    """Wire settings, OIDC adapter, stores, services and the transport adapter.

    Building performs no network call; the provider is first contacted by the
    first login. A client passed in is owned by the caller.
    """
    client = http_client or httpx.Client()
    owned = http_client is None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if owned:
                client.close()

    sessions = SessionManager(InMemorySessionStore(), settings.session)
    login = LoginService(
        OidcIdentityProvider(settings.oidc, client),
        InMemoryLoginStore(),
        sessions,
        settings.login,
    )
    return create_app(
        sessions,
        cookie=settings.cookie,
        clock=clock,
        login=login,
        post_login_redirect=settings.post_login_path,
        lifespan=lifespan,
    )
