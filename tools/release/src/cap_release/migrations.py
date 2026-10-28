"""The migration stage of the deploy path (WP-CICD-003, NFR-DEP-004).

Release-required schema migrations run through the versioned migration tooling, with
status anyone can read, and a stage that halts the deployment before any rollout when
the database cannot be brought to the release's target.

Halt semantics (forward only, 02 Expand -> Migrate -> Contract):

* a ledger that diverges from the release (a different version or checksum at a position,
  or a version this release does not know) halts before anything is applied;
* an unreadable database halts before anything is applied;
* a failed apply halts before the rollout; each migration is applied in its own
  transaction by the tooling, so an earlier one stays applied and a failing one leaves no
  trace; the failure message states where the database was left;
* a database that is not at the target after the apply fails the stage;
* the schema is never reverted by a rollback: rolling the application back leaves the
  schema at the target, which is why a migration must be backward compatible with the
  previous release (Expand before Contract).

No error text ever contains a connection string or a password.
"""

from __future__ import annotations

import hashlib
import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast

from cap_release.registry import ImageRegistry, Migration, migration_files

CORE_SOURCE = "services/manufacturing-core/src"


class MigrationError(Exception):
    """The migration stage cannot pass; the message is safe to record."""


@dataclass(frozen=True)
class Entry:
    version: str
    sha256: str


@dataclass(frozen=True)
class MigrationState:
    """Where a database stands against the migrations of a release."""

    state: str  # EMPTY, BEHIND, CURRENT or DIVERGED
    applied: tuple[str, ...]
    pending: tuple[str, ...]
    detail: str = ""

    def as_dict(self, component: str, head: str) -> dict[str, Any]:
        return {
            "component": component,
            "head": head,
            "state": self.state,
            "applied": list(self.applied),
            "pending": list(self.pending),
            "detail": self.detail,
        }


class MigrationBackend(Protocol):
    def ledger(self) -> list[Entry] | None:
        """The applied migrations in order, or None when the ledger does not exist yet."""
        ...

    def apply(self) -> bool:
        """Apply the pending migrations; True when something was applied, False on replay."""
        ...


def expected_ledger(root: Path, migration: Migration) -> list[Entry]:
    """What a database at this checkout's head must hold: version and checksum per file.

    The checksum is the SHA-256 of the script text, the same value the tooling records.
    """
    return [
        Entry(path.stem, hashlib.sha256(path.read_text("utf-8").encode()).hexdigest())
        for path in migration_files(root, migration)
    ]


def classify(expected: list[Entry], ledger: list[Entry] | None) -> MigrationState:
    """EMPTY, BEHIND, CURRENT or DIVERGED; a diverged ledger is never applied over."""
    if not ledger:
        return MigrationState("EMPTY", (), tuple(e.version for e in expected))
    for position, row in enumerate(ledger):
        if position >= len(expected):
            return MigrationState(
                "DIVERGED",
                tuple(r.version for r in ledger),
                (),
                f"the database holds {row.version}, a version this release does not know",
            )
        want = expected[position]
        if row.version != want.version:
            return MigrationState(
                "DIVERGED",
                tuple(r.version for r in ledger),
                (),
                f"position {position + 1} holds {row.version}, the release expects {want.version}",
            )
        if row.sha256 != want.sha256:
            return MigrationState(
                "DIVERGED",
                tuple(r.version for r in ledger),
                (),
                f"{row.version} was applied with a different checksum than this release carries",
            )
    applied = tuple(r.version for r in ledger)
    pending = tuple(e.version for e in expected[len(ledger) :])
    return MigrationState("BEHIND" if pending else "CURRENT", applied, pending)


def read_state(backend: MigrationBackend, expected: list[Entry]) -> MigrationState:
    return classify(expected, backend.ledger())


def run_stage(
    root: Path, migration: Migration, target: str, backend: MigrationBackend
) -> str:
    """Pre-check, apply, post-check. Returns the stage detail; raises MigrationError to halt."""
    expected = expected_ledger(root, migration)
    if not expected:
        raise MigrationError(f"{migration.component} has no migration to run")
    head = expected[-1].version
    wanted = f"{migration.component}:{head}"
    if target != wanted:
        raise MigrationError(
            f"the release targets {target} but this checkout's head is {wanted}"
        )
    try:
        before = read_state(backend, expected)
    except MigrationError as exc:
        raise MigrationError(f"pre-check failed, nothing applied: {exc}") from exc
    if before.state == "DIVERGED":
        raise MigrationError(f"pre-check halted, nothing applied: {before.detail}")
    if before.state == "CURRENT":
        return f"database already at {head}; nothing to apply"
    try:
        backend.apply()
    except MigrationError as exc:
        raise MigrationError(f"{exc}; {_left_at(backend, expected)}") from exc
    try:
        after = read_state(backend, expected)
    except MigrationError as exc:
        raise MigrationError(f"post-check could not read the database: {exc}") from exc
    if after.state != "CURRENT":
        raise MigrationError(
            f"post-check failed: the database is {after.state} after the apply ({after.detail or 'pending ' + ', '.join(after.pending)})"
        )
    return f"applied {', '.join(before.pending)}; database at {head}"


def _left_at(backend: MigrationBackend, expected: list[Entry]) -> str:
    """Where the database was left after a failed apply, best effort and never raising."""
    try:
        state = read_state(backend, expected)
    except MigrationError:
        return "the database could not be read afterwards"
    last = state.applied[-1] if state.applied else "no migration"
    return (
        f"the database was left at {last} ({state.state}); the schema is not reverted"
    )


@dataclass
class CoreBackend:
    """The Core migration tooling (WP-CORE-007), used through its Python API.

    The checkout's own copy of the tooling is imported, so a release is migrated by the
    tooling of its commit. The CLI hides why it failed and cannot tell an empty database
    from an unreadable one; the API can, and only fixed messages are ever surfaced.
    """

    root: Path
    dsn: str = field(repr=False)
    runtime_role: str

    def _core(self) -> Any:
        source = str(self.root / CORE_SOURCE)
        if source not in sys.path:
            sys.path.insert(0, source)
        try:
            return importlib.import_module("manufacturing_core.migrate")
        except ImportError as exc:
            raise MigrationError(
                f"the Core migration tooling cannot be imported: {exc.name}"
            ) from exc

    def ledger(self) -> list[Entry] | None:
        core = self._core()
        try:
            rows = cast("list[Any]", core.status(self.dsn))
        except Exception as exc:  # noqa: BLE001 - classified below, never printed raw
            if type(exc).__name__ in {"UndefinedTable", "InvalidSchemaName"}:
                return None
            if isinstance(exc, ValueError):  # the tooling's own fixed contract messages
                raise MigrationError(f"the database could not be read ({exc})") from exc
            raise MigrationError(
                f"the database could not be read ({type(exc).__name__})"
            ) from exc
        return [Entry(str(r.version), str(r.sha256)) for r in rows]

    def apply(self) -> bool:
        core = self._core()
        try:
            return bool(core.migrate(self.dsn, self.runtime_role))
        except ValueError as exc:  # the tooling's own fixed contract messages
            raise MigrationError(f"the migration was refused: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise MigrationError(
                f"the migration failed ({type(exc).__name__})"
            ) from exc


def backend_from_environment(root: Path) -> CoreBackend:
    """The operator supplies the migration identity and the restricted runtime role."""
    dsn = os.environ.get("CAP_MIGRATION_DSN", "")
    role = os.environ.get("CAP_RUNTIME_ROLE", "")
    if not dsn or not role:
        raise MigrationError(
            "migration needs CAP_MIGRATION_DSN and CAP_RUNTIME_ROLE in the environment"
        )
    return CoreBackend(root=root, dsn=dsn, runtime_role=role)


def migration_for(registry: ImageRegistry, target: str) -> Migration:
    """The declared migration set a bound target refers to (single-component releases)."""
    component = target.split(":", 1)[0]
    for migration in registry.migrations:
        if migration.component == component:
            return migration
    raise MigrationError(
        f"the release targets {target} but the registry declares no such migration set"
    )
