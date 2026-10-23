"""Location and health of the locked toolchain environment (``uv sync --project ci``).

uv keeps the environment in ``ci/.venv`` unless ``UV_PROJECT_ENVIRONMENT`` points
elsewhere (a relative value is resolved against the project directory ``ci/``).
An environment created by another account can look present but be unusable:
its interpreter link points into a home directory this user cannot read. That
case must be reported with the exact way out, never repaired silently.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

ENV_VAR = "UV_PROJECT_ENVIRONMENT"
PROJECT = "ci"
PERSONAL_ENV = "$HOME/.venvs/cap-ci"


def environment_path(root: Path, environ: Mapping[str, str]) -> Path:
    configured = environ.get(ENV_VAR)
    if not configured:
        return root / PROJECT / ".venv"
    path = Path(configured).expanduser()
    return path if path.is_absolute() else root / PROJECT / path


def interpreter(path: Path) -> Path:
    return path / "bin" / "python"


def owner(path: Path) -> str | None:
    try:
        return path.owner()
    except (OSError, KeyError, NotImplementedError):
        return None


def problem(path: Path) -> str | None:
    """Why the environment cannot be used, or None if it is usable."""
    python = interpreter(path)
    try:
        resolved = python.resolve(strict=True)
    except OSError as exc:
        return f"{python} does not resolve: {exc.strerror or exc}"
    except RuntimeError as exc:  # symlink loop
        return f"{python} does not resolve: {exc}"
    if not os.access(resolved, os.X_OK):
        return f"{python} points to {resolved}, which this user cannot execute"
    return None


def remediation(path: Path, current_user: str) -> str:
    holder = owner(path)
    if holder is None or holder == current_user:
        return (
            f"Remove the derived environment and recreate it: rm -rf {path} "
            "&& mfgctl bootstrap"
        )
    return (
        f"The environment belongs to {holder}; use a personal one instead: "
        f'export {ENV_VAR}="{PERSONAL_ENV}" (add it to ~/.bashrc), '
        "then mfgctl bootstrap"
    )
