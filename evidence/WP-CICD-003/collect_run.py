"""Produce RUN-CICD-003-DEV-NNN: the WP-CICD-003 migration run on the shared host.

Run from the repository root on a clean checkout of main, after the `release` workflow
has published the ReleaseManifest of a main commit that binds a schema target:

    uv run --project ci --locked python evidence/WP-CICD-003/collect_run.py <release-run-id> [NNN]

It downloads that run's ReleaseManifest, checks out the release commit in a throw-away
worktree, starts a disposable PostgreSQL container with the two non-administrative roles
the Core tooling requires, and with the release tooling of that commit:

1. reads the status of an empty database (`migration-status`, exit 1);
2. runs the migration stage for the manifest's schema target (applies, post-check passes);
3. reads the status again (exit 0) and replays the stage (nothing to apply);
4. diverges the ledger checksum and shows the stage halts before anything is applied;
5. uses a wrong password and shows the halt text contains no password or DSN.

Every command is a real invocation; exit codes and output are recorded as observed.
Host paths and the host name are replaced with placeholders. The database is removed
at the end. The password is generated per run and never written to the evidence.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUN_ID = "RUN-CICD-003-DEV-" + (sys.argv[2] if len(sys.argv) > 2 else "001")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
REPO = "Asperant/critical-aerospace-manufacturing"
IMAGE = "postgres:18-alpine"

STAGE = """
import json, sys
from pathlib import Path
from cap_release.migrations import MigrationError, CoreBackend, migration_for, run_stage
from cap_release.registry import load_registry
root = Path.cwd()
manifest = json.loads(Path(sys.argv[1]).read_text("utf-8"))
target = manifest["database_schema_target"]["identity"]
registry = load_registry(root)
backend = CoreBackend(root, sys.argv[2], sys.argv[3])
try:
    print("PASSED", run_stage(root, migration_for(registry, target), target, backend))
except MigrationError as exc:
    print("HALTED", exc)
    raise SystemExit(1)
"""


def sh(
    *argv: str, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv), capture_output=True, text=True, check=False, cwd=cwd, env=env
    )


def main() -> int:
    if len(sys.argv) not in {2, 3} or not sys.argv[1].isdigit():
        print("usage: collect_run.py <release-run-id> [NNN]", file=sys.stderr)
        return 2
    release_run = sys.argv[1]
    root = Path(sh("git", "rev-parse", "--show-toplevel").stdout.strip())
    os.chdir(root)
    if sh("git", "status", "--porcelain").stdout.strip():
        print("Refusing to run: commit or stash local changes first.", file=sys.stderr)
        return 2
    out = root / "evidence" / "WP-CICD-003" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="cicd003-"))
    password = secrets.token_urlsafe(24)
    runtime_password = secrets.token_urlsafe(24)
    secrets_to_hide = [password, runtime_password]
    replacements = [
        (str(Path.home()), "<home>"),
        (str(root), "<repo>"),
        (str(work), "<tmp>"),
        (socket.gethostname(), "<host>"),
    ]

    def clean(text: str) -> str:
        text = ANSI.sub("", text)
        for old, new in replacements:
            text = text.replace(old, new)
        for secret in secrets_to_hide:
            text = text.replace(secret, "<secret>")
        return (
            "\n".join(line.rstrip() for line in text.splitlines()).rstrip("\n") + "\n"
        )

    steps: list[dict[str, Any]] = []

    def record(step: str, code: int, note: str, output: str) -> str:
        text = clean(output)
        (out / f"{step}.txt").write_text(text, encoding="utf-8")
        steps.append({"step": step, "exit_code": code, "note": note, "output": f"{step}.txt"})
        print(f"{step:<26} exit={code} {note}")
        return text

    # 1. the release manifest of the published run
    mdir = work / "manifest"
    done = sh(
        "gh", "run", "download", release_run, "-R", REPO, "-D", str(mdir),
        "--pattern", "release-manifest-*",
    )
    manifest_path = next(mdir.rglob("release-manifest.json"), None)
    if done.returncode != 0 or manifest_path is None:
        print(done.stderr, file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text("utf-8"))
    target = (manifest.get("database_schema_target") or {}).get("identity")
    commit = manifest["source"]["commit"]
    (out / "release-manifest.json").write_text(
        clean(json.dumps(manifest, indent=2, sort_keys=True)), encoding="utf-8"
    )
    record("manifest", 0, f"{manifest['release_id']} binds {target}", f"{manifest['release_id']} {target}")
    if not target:
        print("The manifest binds no schema target.", file=sys.stderr)
        return 2

    tree = work / "release-checkout"
    sh("git", "fetch", "--quiet", "origin", "main")
    if sh("git", "worktree", "add", "--detach", str(tree), commit).returncode != 0:
        return 2

    name = "cap-cicd003-" + secrets.token_hex(4)
    port = ""
    result = "FAILED"
    try:
        # 2. a disposable PostgreSQL with the two non-administrative roles
        admin_password = secrets.token_urlsafe(24)
        secrets_to_hide.append(admin_password)
        started = sh(
            "docker", "run", "-d", "--rm", "--name", name,
            "-e", f"POSTGRES_PASSWORD={admin_password}",
            "-p", "127.0.0.1::5432", "--memory", "512m", IMAGE,
        )
        if started.returncode != 0:
            print(started.stderr, file=sys.stderr)
            return 2
        for _ in range(60):
            ready = sh("docker", "exec", name, "pg_isready", "-U", "postgres")
            if ready.returncode == 0:
                break
            time.sleep(1)
        time.sleep(2)
        mapping = sh("docker", "port", name, "5432/tcp").stdout.strip()
        port = mapping.rsplit(":", 1)[-1]
        db, mig_role, run_role = "cap_migration_run", "cap_migration", "cap_runtime"

        def psql(sql: str) -> subprocess.CompletedProcess[str]:
            return sh("docker", "exec", name, "psql", "-U", "postgres", "-d", db if sql.startswith("--db ") else "postgres", "-v", "ON_ERROR_STOP=1", "-c", sql.removeprefix("--db "))

        for stmt in (
            f"CREATE ROLE {mig_role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS",
            f"CREATE ROLE {run_role} LOGIN PASSWORD '{runtime_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS",
            f"CREATE DATABASE {db}",
            f"GRANT CREATE ON DATABASE {db} TO {mig_role}",
        ):
            if psql(stmt).returncode != 0:
                print("could not prepare the disposable database", file=sys.stderr)
                return 2
        record("database", 0, "disposable PostgreSQL 18 and two non-administrative roles", f"{IMAGE} on loopback, roles {mig_role} and {run_role}")

        dsn = f"postgresql://{mig_role}:{password}@127.0.0.1:{port}/{db}"
        wrong = f"postgresql://{mig_role}:not-the-password@127.0.0.1:{port}/{db}"
        base = {**os.environ, "PYTHONPATH": "tools/release/src"}
        env = {**base, "CAP_MIGRATION_DSN": dsn, "CAP_RUNTIME_ROLE": run_role}
        uv = ["uv", "run", "--project", "ci", "--locked", "python"]
        status = [*uv, "-m", "cap_release", "migration-status"]
        stage = [*uv, "-c", STAGE, str(manifest_path), dsn, run_role]

        p = sh(*status, cwd=tree, env=env)
        record("status-empty", p.returncode, "empty database: pending migrations (exit 1)", p.stdout + p.stderr)
        empty_ok = p.returncode == 1

        p = sh(*stage, cwd=tree, env=base)
        text = record("apply", p.returncode, "the migration stage applies and verifies", p.stdout + p.stderr)
        applied_ok = p.returncode == 0 and text.startswith("PASSED applied")

        p = sh(*status, cwd=tree, env=env)
        record("status-current", p.returncode, "database at the target (exit 0)", p.stdout + p.stderr)
        current_ok = p.returncode == 0

        p = sh(*stage, cwd=tree, env=base)
        text = record("replay", p.returncode, "second run is a checksum-verified replay", p.stdout + p.stderr)
        replay_ok = p.returncode == 0 and "nothing to apply" in text

        # 4. a diverged ledger halts before anything is applied
        psql(f"--db UPDATE core.schema_migration SET sha256 = repeat('0', 64) WHERE version = (SELECT min(version) FROM core.schema_migration)")
        p = sh(*stage, cwd=tree, env=base)
        text = record("diverged-ledger", p.returncode, "halts at pre-check, nothing applied (exit 1)", p.stdout + p.stderr)
        diverged_ok = p.returncode == 1 and "nothing applied" in text
        p = sh(*status, cwd=tree, env=env)
        record("status-diverged", p.returncode, "status reports DIVERGED (exit 2)", p.stdout + p.stderr)
        status_diverged_ok = p.returncode == 2

        # 5. a wrong password halts and leaks nothing
        stage_wrong = [*uv, "-c", STAGE, str(manifest_path), wrong, run_role]
        p = sh(*stage_wrong, cwd=tree, env=base)
        text = record("wrong-password", p.returncode, "unreadable database halts (exit 1)", p.stdout + p.stderr)
        leak = any(s in (p.stdout + p.stderr) for s in (*secrets_to_hide, "not-the-password", "postgresql://"))
        wrong_ok = p.returncode == 1 and not leak
        record("secret-scan", 0 if not leak else 1, "no password or connection string in any recorded text", "clean" if not leak else "LEAK")

        result = (
            "PASSED"
            if all([empty_ok, applied_ok, current_ok, replay_ok, diverged_ok, status_diverged_ok, wrong_ok])
            else "FAILED"
        )
    finally:
        if port:
            sh("docker", "rm", "-f", name)
        sh("git", "worktree", "remove", "--force", str(tree))
        shutil.rmtree(work, ignore_errors=True)

    summary = {
        "run_id": RUN_ID,
        "work_package": "WP-CICD-003",
        "kind": "DEV run on the shared host: the published manifest's schema target applied by the release tooling to a disposable PostgreSQL",
        "boundary_mode": "REAL",
        "code_revision": sh("git", "rev-parse", "HEAD").stdout.strip(),
        "release_run": release_run,
        "release_id": manifest["release_id"],
        "release_commit": commit,
        "schema_target": target,
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "result": result,
        "steps": steps,
        "non_zero_explained": {
            "status-empty": "expected: an empty database has pending migrations",
            "diverged-ledger": "expected: the stage halts before applying over a diverged ledger",
            "status-diverged": "expected: DIVERGED is exit 2",
            "wrong-password": "expected: an unreadable database halts",
        },
    }
    (out / "record.json").write_text(
        clean(json.dumps(summary, indent=2, ensure_ascii=False)), encoding="utf-8"
    )
    print(f"Recorded {RUN_ID}: {result}")
    return 0 if result == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
