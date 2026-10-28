"""TEST-CICD-003-002: the migration stage against a REAL PostgreSQL (TEST-DEP-MIGRATION).

A disposable database and two non-administrative roles (the migration identity and the
restricted runtime role) are created on the CI PostgreSQL, exactly as the Core
persistence tests do, and the deploy path's migration stage runs against them. Missing
infrastructure FAILS, never skips.
"""

from __future__ import annotations

import os
import secrets
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
from cap_release.deploy import DeployError, SystemHost
from cap_release.migrations import (
    CoreBackend,
    MigrationError,
    classify,
    expected_ledger,
    migration_for,
    run_stage,
)
from cap_release.registry import load_registry
from psycopg import sql
from psycopg.conninfo import make_conninfo

pytestmark = pytest.mark.integration
REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Disposable:
    admin_dsn: str
    migration_dsn: str
    wrong_password_dsn: str
    migration_role: str
    runtime_role: str
    password: str


def make_database(grant_create: bool) -> Iterator[Disposable]:
    admin_dsn = os.environ.get("CI_PG_DSN")
    if not admin_dsn or os.environ.get("CORE_TEST_DISPOSABLE") != "1":
        pytest.fail(
            "real disposable CI PostgreSQL DSN and explicit opt-in (CORE_TEST_DISPOSABLE=1) required"
        )
    name = "cap_release_" + uuid.uuid4().hex[:12]
    migration_role, runtime_role = name + "_migration", name + "_runtime"
    password = secrets.token_urlsafe(24)
    runtime_password = secrets.token_urlsafe(24)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        created: list[str] = []
        database = False
        try:
            for role, pw in (
                (migration_role, password),
                (runtime_role, runtime_password),
            ):
                admin.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE "
                        "NOINHERIT NOREPLICATION NOBYPASSRLS"
                    ).format(sql.Identifier(role), sql.Literal(pw))
                )
                created.append(role)
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            database = True
            if grant_create:
                admin.execute(
                    sql.SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                        sql.Identifier(name), sql.Identifier(migration_role)
                    )
                )
            yield Disposable(
                admin_dsn=make_conninfo(admin_dsn, dbname=name),
                migration_dsn=make_conninfo(
                    admin_dsn, dbname=name, user=migration_role, password=password
                ),
                wrong_password_dsn=make_conninfo(
                    admin_dsn,
                    dbname=name,
                    user=migration_role,
                    password="not-the-password",
                ),
                migration_role=migration_role,
                runtime_role=runtime_role,
                password=password,
            )
        finally:
            if database:
                admin.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        sql.Identifier(name)
                    )
                )
            for role in reversed(created):
                admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))


@pytest.fixture
def db() -> Iterator[Disposable]:
    yield from make_database(grant_create=True)


@pytest.fixture
def db_without_create() -> Iterator[Disposable]:
    yield from make_database(grant_create=False)


def backend(database: Disposable) -> CoreBackend:
    return CoreBackend(REPO, database.migration_dsn, database.runtime_role)


def migration() -> tuple[object, str]:
    registry = load_registry(REPO)
    expected = expected_ledger(REPO, registry.migrations[0])
    return registry.migrations[0], f"manufacturing-core:{expected[-1].version}"


def test_an_empty_database_is_detected_applied_verified_and_replayed(
    db: Disposable,
) -> None:
    mig = load_registry(REPO).migrations[0]
    expected = expected_ledger(REPO, mig)
    target = f"manufacturing-core:{expected[-1].version}"
    core = backend(db)
    # The real tooling's missing ledger is told apart from an unreadable database.
    assert core.ledger() is None and classify(expected, core.ledger()).state == "EMPTY"
    detail = run_stage(REPO, mig, target, core)
    assert detail.startswith("applied 0001") and expected[-1].version in detail
    assert classify(expected, core.ledger()).state == "CURRENT"
    # A second run is a checksum-verified replay: nothing is applied.
    assert "nothing to apply" in run_stage(REPO, mig, target, core)


def test_a_database_behind_is_brought_to_the_target(db: Disposable) -> None:
    mig = load_registry(REPO).migrations[0]
    expected = expected_ledger(REPO, mig)
    target = f"manufacturing-core:{expected[-1].version}"
    core = backend(db)
    run_stage(REPO, mig, target, core)
    with psycopg.connect(db.admin_dsn, autocommit=True) as admin:
        admin.execute(
            sql.SQL("DELETE FROM core.schema_migration WHERE version = {}").format(
                sql.Literal(expected[-1].version)
            )
        )
    assert classify(expected, core.ledger()).state == "BEHIND"


def test_a_tampered_ledger_halts_before_anything_is_applied(db: Disposable) -> None:
    mig = load_registry(REPO).migrations[0]
    expected = expected_ledger(REPO, mig)
    target = f"manufacturing-core:{expected[-1].version}"
    core = backend(db)
    run_stage(REPO, mig, target, core)
    with psycopg.connect(db.admin_dsn, autocommit=True) as admin:
        admin.execute(
            "UPDATE core.schema_migration SET sha256 = repeat('0', 64) WHERE version = (SELECT min(version) FROM core.schema_migration)"
        )
    with pytest.raises(
        MigrationError, match="pre-check halted, nothing applied.*different checksum"
    ):
        run_stage(REPO, mig, target, core)


def test_an_unreadable_database_halts_and_never_prints_the_password(
    db: Disposable,
) -> None:
    mig = load_registry(REPO).migrations[0]
    expected = expected_ledger(REPO, mig)
    wrong = CoreBackend(REPO, db.wrong_password_dsn, db.runtime_role)
    with pytest.raises(MigrationError) as raised:
        run_stage(REPO, mig, f"manufacturing-core:{expected[-1].version}", wrong)
    text = str(raised.value)
    assert "pre-check failed, nothing applied" in text and "OperationalError" in text
    assert (
        "not-the-password" not in text
        and db.password not in text
        and "postgresql://" not in text
    )


def test_a_migration_identity_without_the_bootstrap_privilege_fails_and_leaves_nothing(
    db_without_create: Disposable,
) -> None:
    mig = load_registry(REPO).migrations[0]
    expected = expected_ledger(REPO, mig)
    core = backend(db_without_create)
    with pytest.raises(MigrationError) as raised:
        run_stage(REPO, mig, f"manufacturing-core:{expected[-1].version}", core)
    text = str(raised.value)
    assert "the migration failed" in text or "the migration was refused" in text
    assert "no migration" in text and db_without_create.password not in text


def test_the_deploy_hosts_migration_stage_uses_the_environment_identity(
    db: Disposable, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, target = migration()
    monkeypatch.setenv("CAP_MIGRATION_DSN", db.migration_dsn)
    monkeypatch.setenv("CAP_RUNTIME_ROLE", db.runtime_role)
    host = SystemHost(REPO)
    first = host.migrate(target)
    assert first.startswith("applied 0001")
    assert "nothing to apply" in host.migrate(target)
    monkeypatch.setenv("CAP_RUNTIME_ROLE", "")
    with pytest.raises(
        DeployError, match="needs CAP_MIGRATION_DSN and CAP_RUNTIME_ROLE"
    ):
        host.migrate(target)


def test_the_registry_resolves_the_target_to_its_set() -> None:
    assert (
        migration_for(load_registry(REPO), migration()[1]).component
        == "manufacturing-core"
    )
