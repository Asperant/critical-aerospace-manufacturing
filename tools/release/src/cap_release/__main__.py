"""Command line: python -m cap_release <command>. Exit 0 ok, 1 problems found, 2 unreadable input."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, cast

from cap_release.deploy import DeployError, SystemHost, deploy
from cap_release.manifest import (
    ManifestError,
    build_manifest,
    canonical_bytes,
    validate_manifest,
)
from cap_release.migrations import (
    MigrationError,
    backend_from_environment,
    expected_ledger,
    read_state,
)
from cap_release.record import validate_record
from cap_release.registry import RegistryError, check_registry, load_registry


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def read_json(path: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(path.read_text("utf-8")))


def cmd_registry_check(_: argparse.Namespace) -> int:
    problems = check_registry(repo_root())
    for problem in problems:
        print(f"PROBLEM {problem}")
    if problems:
        print(f"FAIL: {len(problems)} registry problem(s)")
        return 1
    count = len(load_registry(repo_root()).images)
    print(
        f"PASS: release/images.json lists {count} image(s); every Dockerfile in the repository is listed"
    )
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    root = repo_root()
    registry = load_registry(root)
    digests: dict[str, str] = {}
    sboms: dict[str, str] = {}
    attests: dict[str, str] = {}
    for path in sorted(Path(args.digests_dir).glob("digest-*.json")):
        item = read_json(path)
        name = path.stem.removeprefix("digest-")
        digests[name] = str(item["digest"])
        if item.get("sbom"):
            sboms[name] = str(item["sbom"])
        if item.get("attestation"):
            attests[name] = str(item["attestation"])
    manifest = build_manifest(
        root,
        registry,
        digests,
        commit=args.commit,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        run_url=args.run_url,
        created_at=dt.datetime.now(dt.UTC),
        tag=args.tag,
        sbom_location=sboms,
        attestation_location=attests,
    )
    problems = validate_manifest(manifest)
    if problems:
        for problem in problems:
            print(f"PROBLEM {problem}")
        return 1
    Path(args.out).write_bytes(canonical_bytes(manifest) + b"\n")
    print(f"wrote {args.out}: {manifest['release_id']} with {len(digests)} image(s)")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    problems = validate_manifest(read_json(Path(args.manifest)))
    for problem in problems:
        print(f"PROBLEM {problem}")
    print(
        "PASS: manifest is valid"
        if not problems
        else f"FAIL: {len(problems)} problem(s)"
    )
    return 1 if problems else 0


def cmd_validate_record(args: argparse.Namespace) -> int:
    manifest = read_json(Path(args.manifest)) if args.manifest else None
    problems = validate_record(read_json(Path(args.record)), manifest)
    for problem in problems:
        print(f"PROBLEM {problem}")
    print(
        "PASS: record is consistent"
        if not problems
        else f"FAIL: {len(problems)} problem(s)"
    )
    return 1 if problems else 0


def cmd_migration_status(_: argparse.Namespace) -> int:
    """Where the database stands against this checkout's migrations (read only).

    Exit 0 CURRENT, 1 EMPTY or BEHIND (pending migrations), 2 DIVERGED or unreadable.
    """
    root = repo_root()
    registry = load_registry(root)
    if not registry.migrations:
        print(
            json.dumps(
                {
                    "state": "NOT_APPLICABLE",
                    "detail": "the release declares no migration set",
                }
            )
        )
        return 0
    worst = 0
    for migration in registry.migrations:
        expected = expected_ledger(root, migration)
        head = expected[-1].version if expected else ""
        try:
            state = read_state(backend_from_environment(root), expected)
        except MigrationError as exc:
            print(
                json.dumps(
                    {
                        "component": migration.component,
                        "head": head,
                        "state": "UNREADABLE",
                        "detail": str(exc),
                    },
                    sort_keys=True,
                )
            )
            worst = max(worst, 2)
            continue
        print(json.dumps(state.as_dict(migration.component, head), sort_keys=True))
        worst = max(worst, {"CURRENT": 0, "EMPTY": 1, "BEHIND": 1}.get(state.state, 2))
    return worst


def cmd_deploy(args: argparse.Namespace) -> int:
    root = repo_root()
    outcome = deploy(
        read_json(Path(args.manifest)),
        load_registry(root),
        SystemHost(root, profile=args.profile),
        environment_id=args.environment,
    )
    print(json.dumps(outcome.record, indent=2, sort_keys=True))
    return outcome.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cap_release")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("registry-check").set_defaults(run=cmd_registry_check)
    manifest = sub.add_parser("manifest")
    manifest.add_argument("--digests-dir", required=True)
    manifest.add_argument("--commit", required=True)
    manifest.add_argument("--run-id", type=int, required=True)
    manifest.add_argument("--run-attempt", type=int, default=1)
    manifest.add_argument("--run-url", required=True)
    manifest.add_argument("--tag")
    manifest.add_argument("--out", required=True)
    manifest.set_defaults(run=cmd_manifest)
    validate = sub.add_parser("validate")
    validate.add_argument("manifest")
    validate.set_defaults(run=cmd_validate)
    record = sub.add_parser("validate-record")
    record.add_argument("record")
    record.add_argument("--manifest")
    record.set_defaults(run=cmd_validate_record)
    sub.add_parser("migration-status").set_defaults(run=cmd_migration_status)
    run = sub.add_parser("deploy")
    run.add_argument("--manifest", required=True)
    run.add_argument("--environment", default="integration")
    run.add_argument("--profile", default="full")
    run.set_defaults(run=cmd_deploy)
    args = parser.parse_args(argv)
    try:
        return int(args.run(args))
    except (
        OSError,
        ValueError,
        KeyError,
        RegistryError,
        ManifestError,
        DeployError,
    ) as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
