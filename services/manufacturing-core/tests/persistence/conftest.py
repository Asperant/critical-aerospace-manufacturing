"""Disposable real database, two independent login roles; never shared state."""

import os
import secrets
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import psycopg
import pytest
from manufacturing_core.database import connect_runtime
from manufacturing_core.migrate import migrate
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow


@dataclass(frozen=True)
class Database:
    admin_dsn: str
    migration_dsn: str
    runtime_dsn: str
    migration_role: str
    runtime_role: str


@pytest.fixture(scope="session")
def database() -> Iterator[Database]:
    admin_dsn = os.environ.get("CI_PG_DSN")
    if not admin_dsn or os.environ.get("CORE_TEST_DISPOSABLE") != "1":
        pytest.fail("real disposable CI PostgreSQL DSN and explicit opt-in required")
    suffix = uuid.uuid4().hex[:12]
    name = "core_test_" + suffix
    migration_role, runtime_role = name + "_migration", name + "_runtime"
    # Generated only for disposable test identities; never configuration defaults.
    migration_password, runtime_password = (
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(32),
    )
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        assert admin.info.server_version >= 180000
        created_roles: list[str] = []
        created_database = False
        try:
            for role, password in (
                (migration_role, migration_password),
                (runtime_role, runtime_password),
            ):
                admin.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                    ).format(sql.Identifier(role), sql.Literal(password))
                )
                created_roles.append(role)
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            created_database = True
            admin.execute(
                sql.SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                    sql.Identifier(name), sql.Identifier(migration_role)
                )
            )
            settings = Database(
                admin_dsn=make_conninfo(admin_dsn, dbname=name),
                migration_dsn=make_conninfo(
                    admin_dsn,
                    dbname=name,
                    user=migration_role,
                    password=migration_password,
                ),
                runtime_dsn=make_conninfo(
                    admin_dsn, dbname=name, user=runtime_role, password=runtime_password
                ),
                migration_role=migration_role,
                runtime_role=runtime_role,
            )
            assert migrate(settings.migration_dsn, runtime_role) is True
            admin.execute(
                sql.SQL("REVOKE CREATE ON DATABASE {} FROM {}").format(
                    sql.Identifier(name), sql.Identifier(migration_role)
                )
            )
            yield settings
        finally:
            if created_database:
                admin.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        sql.Identifier(name)
                    )
                )
            for role in reversed(created_roles):
                admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))


@pytest.fixture
def connection(database: Database) -> Iterator[psycopg.Connection[DictRow]]:
    with (
        connect_runtime(database.runtime_dsn) as conn,
        conn.transaction(force_rollback=True),
    ):
        yield conn
