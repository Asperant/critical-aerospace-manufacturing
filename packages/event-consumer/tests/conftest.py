"""Disposable PostgreSQL database and separate restricted migration/runtime roles."""

import os
import secrets
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import psycopg
import pytest
from cap_event_consumer.migrate import migrate
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow, dict_row


@dataclass(frozen=True)
class Database:
    admin_dsn: str
    migration_dsn: str
    runtime_dsn: str
    runtime_role: str


@pytest.fixture(scope="session")
def database() -> Iterator[Database]:
    admin_dsn = os.environ.get("CI_PG_DSN")
    if not admin_dsn or os.environ.get("EVT_TEST_DISPOSABLE") != "1":
        pytest.fail("real disposable PostgreSQL DSN and explicit opt-in required")
    name = "evt_test_" + uuid.uuid4().hex[:12]
    migration_role, runtime_role = name + "_migration", name + "_runtime"
    passwords = [secrets.token_urlsafe(32), secrets.token_urlsafe(32)]
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        assert admin.info.server_version >= 180000
        created_roles: list[str] = []
        created_database = False
        try:
            for role, password in zip(
                (migration_role, runtime_role), passwords, strict=False
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
            settings = Database(
                admin_dsn=make_conninfo(admin_dsn, dbname=name),
                migration_dsn=make_conninfo(
                    admin_dsn, dbname=name, user=migration_role, password=passwords[0]
                ),
                runtime_dsn=make_conninfo(
                    admin_dsn, dbname=name, user=runtime_role, password=passwords[1]
                ),
                runtime_role=runtime_role,
            )
            with psycopg.connect(settings.admin_dsn) as setup:
                setup.execute(
                    sql.SQL("CREATE SCHEMA consumer AUTHORIZATION {}").format(
                        sql.Identifier(migration_role)
                    )
                )
                setup.execute("REVOKE ALL ON SCHEMA consumer FROM PUBLIC")
            with (
                psycopg.Connection[DictRow].connect(
                    settings.migration_dsn, row_factory=dict_row
                ) as conn,
                conn.transaction(),
            ):
                assert migrate(conn, "consumer", runtime_role) is True
                conn.execute("CREATE TABLE consumer.effect (event_id text NOT NULL)")
                conn.execute(
                    sql.SQL("GRANT SELECT, INSERT ON consumer.effect TO {}").format(
                        sql.Identifier(runtime_role)
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
        psycopg.Connection[DictRow].connect(
            database.runtime_dsn, row_factory=dict_row
        ) as conn,
        conn.transaction(force_rollback=True),
    ):
        yield conn
