"""Operator commands (WP-OBJ-001).

    python -m cap_artifacts ensure-buckets   # admin identity (CAP_S3_ADMIN_*)
    python -m cap_artifacts consistency      # writer identity + CAP_ARTIFACT_REGISTRY_DSN

Exit 0 on success / consistent, 1 on findings, 2 on configuration errors.
Credentials and DSNs are never printed.
"""

from __future__ import annotations

import os
import sys

from cap_artifacts.errors import StoreError
from cap_artifacts.store import ArtifactStore, S3Client, StoreConfig


def ensure_buckets() -> int:
    client = S3Client(StoreConfig.from_env(role="admin"))
    try:
        for bucket in ArtifactStore(client).ensure_buckets():
            print(f"bucket ready: {bucket}")
    finally:
        client.close()
    return 0


def consistency() -> int:
    from cap_artifacts.registry import Registry, check_consistency

    dsn = os.environ.get("CAP_ARTIFACT_REGISTRY_DSN", "")
    if not dsn:
        print("CAP_ARTIFACT_REGISTRY_DSN is not set", file=sys.stderr)
        return 2
    client = S3Client(StoreConfig.from_env())
    try:
        registry = Registry.connect(dsn)
    except Exception:  # connection errors may echo connection details; never print them
        client.close()
        print("cannot connect to the artifact registry", file=sys.stderr)
        return 2
    try:
        report = check_consistency(registry, client.iter_keys)
    finally:
        registry.close()
        client.close()
    for title, items in (
        ("missing bytes", report.missing_bytes),
        ("orphan objects", report.orphan_objects),
        ("stale in flight", report.stale_in_flight),
    ):
        for item in items:
            print(f"{title}: {item}")
    print("CONSISTENT" if report.consistent else "INCONSISTENT")
    return 0 if report.consistent else 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    commands = {"ensure-buckets": ensure_buckets, "consistency": consistency}
    if len(args) != 1 or args[0] not in commands:
        print(
            f"usage: python -m cap_artifacts {{{'|'.join(commands)}}}", file=sys.stderr
        )
        return 2
    try:
        return commands[args[0]]()
    except StoreError as exc:
        print(f"{args[0]} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
