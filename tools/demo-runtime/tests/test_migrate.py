from __future__ import annotations

import psycopg
import pytest
from cap_demo_runtime.migrate import _retry_database_startup


def test_migration_retries_transient_postgres_startup_and_then_succeeds() -> None:
    calls = 0
    delays: list[float] = []

    def operation() -> None:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise psycopg.OperationalError("database system is starting up")

    _retry_database_startup(operation, attempts=3, sleep=delays.append)

    assert calls == 3
    assert delays == [1.0, 2.0]


def test_migration_fails_closed_after_bounded_retries() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise psycopg.OperationalError("connection refused")

    with pytest.raises(RuntimeError, match="after 2 attempts"):
        _retry_database_startup(operation, attempts=2, sleep=lambda _: None)
    assert calls == 2
