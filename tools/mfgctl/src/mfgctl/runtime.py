"""``profile``, ``smoke`` and ``scenario`` (01 Item 74 §20–24, §30–31, §36).

Thin orchestration (DX-INV-03): each command turns a registry entry into one
argv and runs it without a shell. The commands themselves, the Compose files and
the smoke paths belong to the capability owners (WP-PLAT-001 and later WPs).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mfgctl.probe import NOT_FOUND, TIMED_OUT, StreamRunner
from mfgctl.registry import Registry

PROFILE_TIMEOUT = 900.0


@dataclass(frozen=True)
class Action:
    label: str
    argv: tuple[str, ...]
    timeout: float


@dataclass(frozen=True)
class ActionResult:
    action: Action
    returncode: int
    duration_ms: int

    @property
    def passed(self) -> bool:
        return self.returncode == 0

    def summary(self) -> str:
        if self.passed:
            state = "PASS"
        elif self.returncode == NOT_FOUND:
            state = "FAIL (command not found)"
        elif self.returncode == TIMED_OUT:
            state = f"FAIL (timed out after {self.action.timeout:.0f} s)"
        else:
            state = f"FAIL (exit {self.returncode})"
        return f"{self.action.label}: {state} in {self.duration_ms / 1000:.1f} s"


def profile_up(registry: Registry, name: str) -> Action:
    registry.profile(name)
    argv = [*registry.compose_args(), "--profile", name, "up", "--detach", "--wait"]
    return Action(f"profile up {name}", tuple(argv), PROFILE_TIMEOUT)


def profile_down(registry: Registry, name: str) -> Action:
    registry.profile(name)
    argv = [*registry.compose_args(), "--profile", name, "down"]
    return Action(f"profile down {name}", tuple(argv), PROFILE_TIMEOUT)


def status(registry: Registry) -> Action:
    argv = [*registry.compose_args(), "ps", "--all"]
    return Action("status", tuple(argv), 60.0)


def smoke(registry: Registry, name: str) -> Action:
    capability = registry.capability(name)
    return Action(f"smoke {name}", capability.smoke, float(capability.timeout_s))


def scenario(registry: Registry, identity: str) -> Action:
    entry = registry.scenario(identity)
    return Action(f"scenario run {identity}", entry.command, float(entry.timeout_s))


def execute(
    action: Action,
    root: Path,
    runner: StreamRunner,
    clock: Callable[[], float] = time.monotonic,
) -> ActionResult:
    started = clock()
    code = runner(action.argv, {}, root, action.timeout)
    return ActionResult(action, code, round((clock() - started) * 1000))


def render_profiles(registry: Registry) -> str:
    lines = [f"Profiles ({registry.path})"]
    for profile in registry.profiles:
        members = [c.name for c in registry.capabilities if c.profile == profile.name]
        lines.append(f"  {profile.name:<14} {profile.description}")
        if members:
            lines.append(f"  {'':<14} smoke: {', '.join(members)}")
    return "\n".join(lines)


def render_scenarios(registry: Registry) -> str:
    if not registry.scenarios:
        return f"No scenarios declared in {registry.path}."
    lines = [f"Scenarios ({registry.path})"]
    for entry in registry.scenarios:
        lines.append(f"  {entry.id:<10} [{entry.profile}] {entry.description}")
    return "\n".join(lines)
