"""Read-only CI adapter for the registry, compatibility detector and version gate."""

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .authority import ProducerAuthorities
from .compatibility import compare_contracts, enforce_version_policy
from .errors import ContractError
from .registry import ContractDeclaration, FileRef, Registry, load_schema

_PACKAGE = "packages/contracts/"
_REGISTRY = _PACKAGE + "registry/"
_APPROVALS = _PACKAGE + "schema-refs.json"
_AUTHORITIES = _PACKAGE + "producer-authorities.json"


def _pins(root: Path) -> tuple[FileRef, ...]:
    path = root / _APPROVALS
    if not path.exists():
        return ()
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError
        pins = tuple(FileRef.from_value(value, "schema_refs") for value in entries)
        if len({pin.path for pin in pins}) != len(pins) or any(
            not pin.path.startswith(_PACKAGE) for pin in pins
        ):
            raise ValueError
        return pins
    except (OSError, ValueError):
        raise ContractError("SCHEMA_REFS_INVALID") from None


def _documents(
    root: Path, *, authorities: ProducerAuthorities, baseline: bool = False
) -> dict[str, tuple[ContractDeclaration, dict[str, Any], dict[str, Any] | None]]:
    directory = root / _REGISTRY
    if not directory.exists():
        if baseline:
            return {}
        raise ContractError("REGISTRY_MISSING")
    registry = Registry.load(directory)
    if not registry.contract_ids() and not baseline:
        raise ContractError("REGISTRY_EMPTY")
    registry.verify_authorities(authorities, repo_root=root)
    pins = _pins(root)
    for pin in pins:
        load_schema(pin, root, schema_refs=pins)
    registry.verify(root, schema_refs=pins)
    result = {}
    for contract_id in registry.contract_ids():
        declaration = registry.get(contract_id)
        result[contract_id] = (
            declaration,
            load_schema(declaration.output_schema, root, schema_refs=pins),
            None
            if declaration.input_schema is None
            else load_schema(declaration.input_schema, root, schema_refs=pins),
        )
    # Reject non-JSON values (for example NaN in annotations) even for new families.
    for declaration, output, request in result.values():
        json.dumps(
            [asdict(declaration), output, request], sort_keys=True, allow_nan=False
        )
    return result


def check_versions(old_root: Path, new_root: Path) -> dict[str, Any]:
    """Validate both snapshots, then gate changed/next-major declarations only.

    A new family has no predecessor: boundary validity is checked, compatibility
    is not claimed. Exact unchanged declarations and resolved documents need no
    change decision. Removed declarations fail closed pending an explicit policy.
    """
    report: dict[str, Any] = {
        "schema_version": "cap-contract-ci-v1",
        "status": "FAIL",
        "validated": 0,
        "compared": 0,
        "added": 0,
        "unchanged": 0,
        "failures": [],
    }
    try:
        candidate_authorities = ProducerAuthorities.load(new_root / _AUTHORITIES)
    except ContractError as error:
        report["failures"].append({"stage": "candidate", "code": error.code})
        return report
    snapshots = []
    for stage, root in (("baseline", old_root), ("candidate", new_root)):
        try:
            # Pre-model history is checked against the explicit candidate model;
            # no declaration is grandfathered out of authority validation.
            authorities = (
                ProducerAuthorities.load(root / _AUTHORITIES)
                if (root / _AUTHORITIES).exists()
                else candidate_authorities
            )
            snapshots.append(
                _documents(root, authorities=authorities, baseline=stage == "baseline")
            )
        except ContractError as error:
            report["failures"].append({"stage": stage, "code": error.code})
        except Exception:
            report["failures"].append(
                {"stage": stage, "code": "CONTRACT_INPUT_INVALID"}
            )
    if report["failures"]:
        return report
    old, new = snapshots
    report["validated"] = len(new)
    for contract_id in sorted(old.keys() - new.keys()):
        report["failures"].append(
            {"contract_id": contract_id, "code": "CONTRACT_REMOVED"}
        )
    for contract_id, (declaration, output, request) in sorted(new.items()):
        prior = old.get(contract_id)
        if prior is None:
            family = [
                entry
                for entry in old.values()
                if entry[0].parsed_id.family == declaration.parsed_id.family
            ]
            if not family:
                report["added"] += 1
                continue
            prior = max(family, key=lambda entry: entry[0].version)
        before, old_output, old_request = prior
        try:
            if json.dumps(
                [asdict(before), old_output, old_request],
                sort_keys=True,
                allow_nan=False,
            ) == json.dumps(
                [asdict(declaration), output, request], sort_keys=True, allow_nan=False
            ):
                report["unchanged"] += 1
                continue
            report["compared"] += 1
            compatibility = compare_contracts(
                before,
                declaration,
                old_output_schema=old_output,
                new_output_schema=output,
                old_input_schema=old_request,
                new_input_schema=request,
            )
            enforce_version_policy(
                before.contract_id, declaration.contract_id, compatibility
            )
        except ContractError as error:
            report["failures"].append({"contract_id": contract_id, "code": error.code})
        except Exception:
            report["failures"].append(
                {"contract_id": contract_id, "code": "CONTRACT_INPUT_INVALID"}
            )
    report["status"] = "FAIL" if report["failures"] else "PASS"
    return report


def _git(root: Path, *args: str) -> bytes:
    process = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if process.returncode:
        raise ContractError("GIT_INPUT_UNAVAILABLE")
    return process.stdout


def _revision(root: Path, value: str) -> str:
    return (
        _git(root, "rev-parse", "--verify", "--end-of-options", value + "^{commit}")
        .decode()
        .strip()
    )


def _snapshot(repo: Path, revision: str, destination: Path) -> None:
    """Materialize only declarations, explicit approvals and their pinned files.

    Git blobs are read without checkout, hooks, network access or symlink following.
    Missing blobs remain missing so the existing loader rejects their FileRefs.
    """
    entries = {}
    for line in _git(repo, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if line:
            metadata, name = line.split(b"\t", 1)
            mode, kind, digest = metadata.decode().split()
            entries[name.decode()] = (mode, kind, digest)

    def materialize(path: str) -> None:
        entry = entries.get(path)
        if entry is None:
            return
        mode, kind, digest = entry
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ContractError("GIT_ENTRY_UNSUPPORTED")
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_git(repo, "cat-file", "blob", digest))

    for path in sorted(entries):
        if path.startswith(_REGISTRY) or path in {
            _REGISTRY.rstrip("/"),
            _APPROVALS,
            _AUTHORITIES,
        }:
            materialize(path)
    if (destination / _REGISTRY).exists():
        registry = Registry.load(destination / _REGISTRY)
        refs = list(_pins(destination))
        for contract_id in registry.contract_ids():
            declaration = registry.get(contract_id)
            refs.extend((declaration.output_schema, *declaration.fixtures))
            if declaration.input_schema is not None:
                refs.append(declaration.input_schema)
        for path in sorted({ref.path for ref in refs}):
            materialize(path)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args and (len(args) != 2 or args[0] != "--base"):
            raise ContractError("ARGUMENT_INVALID")
        repo = Path.cwd()
        base = args[1] if args else os.environ.get("CONTRACT_BASE", "")
        if not base or set(base) == {"0"}:
            base = _git(repo, "merge-base", "HEAD", "origin/main").decode().strip()
        baseline, candidate = _revision(repo, base), _revision(repo, "HEAD")
        with tempfile.TemporaryDirectory(prefix="cap-contract-ci-") as directory:
            old, new = Path(directory) / "baseline", Path(directory) / "candidate"
            old.mkdir()
            new.mkdir()
            _snapshot(repo, baseline, old)
            _snapshot(repo, candidate, new)
            report = check_versions(old, new)
    except ContractError as error:
        report = {
            "schema_version": "cap-contract-ci-v1",
            "status": "FAIL",
            "failures": [{"stage": "snapshot", "code": error.code}],
        }
    except Exception:
        report = {
            "schema_version": "cap-contract-ci-v1",
            "status": "FAIL",
            "failures": [{"stage": "snapshot", "code": "CONTRACT_INPUT_INVALID"}],
        }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
