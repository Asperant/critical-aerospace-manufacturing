"""Capability registry: what ``profile``, ``smoke`` and ``scenario`` operate on.

The registry is the contract ``tools/mfgctl/schemas/capabilities.schema.json``
(schema ``mfgctl.capabilities/v1``). WP-PLAT-001 produces the real file at
``infra/mfgctl/capabilities.json`` (DEP-003); until it exists every command that
needs it stops with an explicit message and runs nothing. ``MFGCTL_REGISTRY``
points to another file (relative paths are resolved from the repository root).

The loader repeats the structural rules of the schema so mfgctl needs no
JSON Schema dependency; the contract tier validates the schema and its example.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PATH = "infra/mfgctl/capabilities.json"
ENV_VAR = "MFGCTL_REGISTRY"
SCHEMA = "mfgctl.capabilities/v1"
OWNERS = frozenset({"Asrın", "Selman", "Batu", "Yavuz"})
NAME = re.compile(r"^[a-z][a-z0-9-]*$")
SCENARIO_ID = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")
DEFAULT_SMOKE_TIMEOUT = 120
DEFAULT_SCENARIO_TIMEOUT = 600


class RegistryMissingError(Exception):
    """No registry file yet (expected until WP-PLAT-001 delivers it)."""


class RegistryInvalidError(Exception):
    """The registry exists but breaks the mfgctl.capabilities/v1 contract."""


@dataclass(frozen=True)
class Profile:
    name: str
    description: str


@dataclass(frozen=True)
class Capability:
    name: str
    owner: str
    profile: str
    smoke: tuple[str, ...]
    timeout_s: int


@dataclass(frozen=True)
class Scenario:
    id: str
    description: str
    profile: str
    command: tuple[str, ...]
    timeout_s: int


@dataclass(frozen=True)
class Registry:
    path: Path
    compose_files: tuple[str, ...]
    profiles: tuple[Profile, ...]
    capabilities: tuple[Capability, ...]
    scenarios: tuple[Scenario, ...]

    def profile(self, name: str) -> Profile:
        return _pick(self.profiles, name, lambda p: p.name, "profile")

    def capability(self, name: str) -> Capability:
        return _pick(self.capabilities, name, lambda c: c.name, "capability")

    def scenario(self, identity: str) -> Scenario:
        return _pick(self.scenarios, identity, lambda s: s.id, "scenario")

    def compose_args(self) -> list[str]:
        args = ["docker", "compose"]
        for file in self.compose_files:
            args += ["-f", file]
        return args


class UnknownNameError(Exception):
    """A profile, capability or scenario name that the registry does not declare."""


def _pick(items: Sequence[Any], key: str, name_of: Any, kind: str) -> Any:
    for item in items:
        if name_of(item) == key:
            return item
    known = ", ".join(name_of(item) for item in items) or "none declared"
    raise UnknownNameError(f"unknown {kind} {key!r}; known: {known}")


def registry_path(root: Path, environ: Mapping[str, str]) -> Path:
    configured = environ.get(ENV_VAR)
    if not configured:
        return root / DEFAULT_PATH
    path = Path(configured).expanduser()
    return path if path.is_absolute() else root / path


def load(root: Path, environ: Mapping[str, str]) -> Registry:
    path = registry_path(root, environ)
    if not path.is_file():
        raise RegistryMissingError(
            f"no capability registry at {path}. Compose profiles, smoke paths and "
            "scenarios arrive with WP-PLAT-001 (DEP-003); nothing was run."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryInvalidError(f"{path}: unreadable: {exc}") from exc
    return parse(data, path)


def _fail(path: Path, where: str, message: str) -> RegistryInvalidError:
    return RegistryInvalidError(f"{path}: {where}: {message}")


def _object(value: Any, path: Path, where: str, required: set[str], optional: set[str]):
    if not isinstance(value, dict):
        raise _fail(path, where, "must be an object")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise _fail(path, where, f"missing {', '.join(sorted(missing))}")
    if extra:
        raise _fail(path, where, f"unexpected {', '.join(sorted(extra))}")
    return value


def _text(
    value: Any, path: Path, where: str, pattern: re.Pattern[str] | None = None
) -> str:
    if not isinstance(value, str) or not value:
        raise _fail(path, where, "must be a non-empty string")
    if pattern is not None and not pattern.fullmatch(value):
        raise _fail(path, where, f"{value!r} does not match {pattern.pattern}")
    return value


def _command(value: Any, path: Path, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _fail(path, where, "must be a non-empty argv list")
    return tuple(_text(part, path, where) for part in value)


def _timeout(value: Any, default: int, path: Path, where: str) -> int:
    if value is None:
        return default
    if type(value) is not int or not 1 <= value <= 3600:
        raise _fail(path, where, "timeout_s must be an integer from 1 to 3600")
    return value


def _list(value: Any, path: Path, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise _fail(path, where, "must be a list")
    return value


def _relative(value: Any, path: Path, where: str) -> str:
    text = _text(value, path, where)
    parts = text.split("/")
    if text.startswith("/") or ".." in parts or "" in parts:
        raise _fail(
            path, where, f"{text!r} must be a relative path inside the repository"
        )
    return text


def parse(data: Any, path: Path) -> Registry:
    top = _object(
        data,
        path,
        "registry",
        {"schema", "compose_files", "profiles", "capabilities", "scenarios"},
        set(),
    )
    if top["schema"] != SCHEMA:
        raise _fail(path, "schema", f"expected {SCHEMA}, found {top['schema']!r}")
    compose = _list(top["compose_files"], path, "compose_files")
    if not compose:
        raise _fail(path, "compose_files", "must name at least one file")
    files = tuple(
        _relative(f, path, f"compose_files[{i}]") for i, f in enumerate(compose)
    )

    profiles: list[Profile] = []
    for i, raw in enumerate(_list(top["profiles"], path, "profiles")):
        where = f"profiles[{i}]"
        item = _object(raw, path, where, {"name", "description"}, set())
        profiles.append(
            Profile(
                _text(item["name"], path, where, NAME),
                _text(item["description"], path, where),
            )
        )
    if not profiles:
        raise _fail(path, "profiles", "must declare at least one profile")
    names = [p.name for p in profiles]
    _unique(names, path, "profiles")

    capabilities: list[Capability] = []
    for i, raw in enumerate(_list(top["capabilities"], path, "capabilities")):
        where = f"capabilities[{i}]"
        item = _object(
            raw, path, where, {"name", "owner", "profile", "smoke"}, {"timeout_s"}
        )
        owner = _text(item["owner"], path, where)
        if owner not in OWNERS:
            raise _fail(path, where, f"owner {owner!r} is not one of {sorted(OWNERS)}")
        capabilities.append(
            Capability(
                _text(item["name"], path, where, NAME),
                owner,
                _known(_text(item["profile"], path, where, NAME), names, path, where),
                _command(item["smoke"], path, where),
                _timeout(item.get("timeout_s"), DEFAULT_SMOKE_TIMEOUT, path, where),
            )
        )
    _unique([c.name for c in capabilities], path, "capabilities")

    scenarios: list[Scenario] = []
    for i, raw in enumerate(_list(top["scenarios"], path, "scenarios")):
        where = f"scenarios[{i}]"
        item = _object(
            raw, path, where, {"id", "description", "profile", "command"}, {"timeout_s"}
        )
        scenarios.append(
            Scenario(
                _text(item["id"], path, where, SCENARIO_ID),
                _text(item["description"], path, where),
                _known(_text(item["profile"], path, where, NAME), names, path, where),
                _command(item["command"], path, where),
                _timeout(item.get("timeout_s"), DEFAULT_SCENARIO_TIMEOUT, path, where),
            )
        )
    _unique([s.id for s in scenarios], path, "scenarios")
    return Registry(path, files, tuple(profiles), tuple(capabilities), tuple(scenarios))


def _known(name: str, names: Sequence[str], path: Path, where: str) -> str:
    if name not in names:
        raise _fail(path, where, f"profile {name!r} is not declared in profiles")
    return name


def _unique(values: Sequence[str], path: Path, where: str) -> None:
    duplicates = sorted({v for v in values if values.count(v) > 1})
    if duplicates:
        raise _fail(path, where, f"duplicate {', '.join(duplicates)}")
