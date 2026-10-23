"""``mfgctl diagnose bundle`` — a shareable diagnostics archive (01 Item 74 §39).

Hook for NFR-DX-008 (bundle ≤ 2 min, unredacted secrets = 0). The bundle is
built from mfgctl's own read-only observations, never from arbitrary files:

- ``doctor.json``: the doctor report;
- ``git.txt``: HEAD, branch and ``git status --short``;
- ``timings.json``: timing summary and the latest records;
- ``versions.json``: mfgctl, Python and platform versions, registry presence.

Environment variables and repository files (``.env`` included) are never
collected. Every text is passed through ``redact`` before it is written, and
the bundle is written to the user's state directory, not into the repository.
Review a bundle before sharing it; redaction is defence in depth.
"""

from __future__ import annotations

import io
import json
import platform
import re
import tarfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from mfgctl import __version__, registry, timing
from mfgctl.doctor import Environment, render_json, run_doctor

SCHEMA = "mfgctl.diagnose/v1"
LATEST_RECORDS = 50
REDACTED = "[REDACTED]"
PATTERNS = (
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S
    ),
)
KEY_VALUE = re.compile(
    r"(?i)\b((?:password|passwd|secret|token|api[_-]?key|access[_-]?key)\w*\s*[=:]\s*)"
    r"(\"[^\"]*\"|'[^']*'|\S+)"
)
URL_CREDENTIALS = re.compile(r"(\b[a-z][a-z0-9+.-]*://)([^/\s:@]+):([^/\s@]+)@")


def redact(text: str) -> str:
    for pattern in PATTERNS:
        text = pattern.sub(REDACTED, text)
    text = KEY_VALUE.sub(lambda m: m.group(1) + REDACTED, text)
    return URL_CREDENTIALS.sub(lambda m: f"{m.group(1)}{m.group(2)}:{REDACTED}@", text)


def _git(env: Environment) -> str:
    lines = []
    for label, args in (
        ("HEAD", ["git", "-C", str(env.root), "rev-parse", "HEAD"]),
        ("branch", ["git", "-C", str(env.root), "branch", "--show-current"]),
        ("status --short", ["git", "-C", str(env.root), "status", "--short"]),
    ):
        result = env.run(args, 15.0)
        body = (
            result.stdout if result.ok else f"unavailable: {result.first_error_line()}"
        )
        lines.append(f"## {label}\n{body}\n")
    return "\n".join(lines)


def collect(env: Environment, environ: Mapping[str, str]) -> dict[str, str]:
    records = timing.load(environ)
    registry_file = registry.registry_path(env.root, environ)
    versions = {
        "schema": SCHEMA,
        "mfgctl": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "registry": str(registry_file),
        "registry_present": registry_file.is_file(),
    }
    payload = {
        "summary": timing.summarize(records),
        "latest": records[-LATEST_RECORDS:],
    }
    files = {
        "doctor.json": render_json(run_doctor(env)),
        "git.txt": _git(env),
        "timings.json": json.dumps(payload, indent=2, ensure_ascii=False),
        "versions.json": json.dumps(versions, indent=2),
    }
    return {name: redact(content) for name, content in files.items()}


def write_bundle(files: Mapping[str, str], target_dir: Path, now: datetime) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = target_dir / f"mfgctl-diagnose-{stamp}.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        for name, content in sorted(files.items()):
            data = content.encode("utf-8")
            info = tarfile.TarInfo(f"mfgctl-diagnose-{stamp}/{name}")
            info.size = len(data)
            info.mtime = int(now.timestamp())
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(data))
    path.chmod(0o600)
    return path


def default_target(environ: Mapping[str, str]) -> Path:
    return timing.state_dir(environ) / "bundles"
