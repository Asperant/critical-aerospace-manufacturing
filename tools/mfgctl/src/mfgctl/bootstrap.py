"""``mfgctl bootstrap`` — prepare the developer environment (01 Item 74 §13–15).

- Idempotent (DX-INV-05): a second run on a prepared machine changes nothing
  and says so.
- It prepares the locked toolchain only; it never starts the platform runtime
  (§15) and never deletes anything. An unusable environment stops bootstrap
  with the exact remediation instead of being removed behind the user's back
  (doctor diagnoses before unsafe repair, DX-INV-06).
- ``--dry-run`` shows the plan and runs nothing but read-only checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mfgctl import venv
from mfgctl.doctor import Environment, Status, check_git, check_uv
from mfgctl.probe import TIMED_OUT

SYNC_TIMEOUT = 900.0
CHANGE_MARKERS = re.compile(
    r"^(?:Creating virtual environment|Installed \d|Uninstalled \d|Removed virtual)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Step:
    name: str
    status: Status
    detail: str
    remediation: str | None = None


@dataclass
class Outcome:
    steps: list[Step] = field(default_factory=list)
    changed: bool = False

    @property
    def failed(self) -> bool:
        return any(step.status is Status.FAIL for step in self.steps)

    @property
    def exit_code(self) -> int:
        return 1 if self.failed else 0


def sync_command(env: Environment) -> list[str]:
    return ["uv", "sync", "--project", str(env.root / venv.PROJECT), "--locked"]


def run_bootstrap(env: Environment, dry_run: bool = False) -> Outcome:
    outcome = Outcome()
    for check in (check_git(env), check_uv(env)):
        status = Status.FAIL if check.status is Status.FAIL else Status.OK
        outcome.steps.append(Step(check.name, status, check.detail, check.remediation))
    if outcome.failed:
        return outcome

    path = venv.environment_path(env.root, env.environ)
    problem = venv.problem(path) if path.exists() else None
    if problem is not None:
        outcome.steps.append(
            Step("venv", Status.FAIL, problem, venv.remediation(path, env.current_user))
        )
        return outcome
    state = "present" if path.exists() else "will be created"
    outcome.steps.append(Step("venv", Status.OK, f"{path} {state}"))

    command = sync_command(env)
    if dry_run:
        outcome.steps.append(Step("sync", Status.OK, "would run: " + " ".join(command)))
        return outcome

    result = env.run(command, SYNC_TIMEOUT)
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode == TIMED_OUT or not result.ok:
        outcome.steps.append(
            Step(
                "sync",
                Status.FAIL,
                result.first_error_line(),
                "If ci/uv.lock is stale run uv lock --project ci and commit it; "
                "otherwise check network access to the package index.",
            )
        )
        return outcome
    outcome.changed = bool(CHANGE_MARKERS.search(output))
    detail = "environment updated" if outcome.changed else "already up to date"
    outcome.steps.append(Step("sync", Status.OK, detail))
    return outcome


def render_text(outcome: Outcome, dry_run: bool) -> str:
    title = "mfgctl bootstrap (dry run)" if dry_run else "mfgctl bootstrap"
    lines = [title]
    for step in outcome.steps:
        lines.append(f"  {step.status.value:<5} {step.name:<5} {step.detail}")
        if step.remediation and step.status is Status.FAIL:
            lines.append(f"  {'':<5} {'':<5} → {step.remediation}")
    if outcome.failed:
        lines.append(
            "Result: FAIL — nothing was removed; fix the step above and rerun."
        )
    elif dry_run:
        lines.append("Result: OK — nothing was changed (dry run).")
    else:
        verdict = "changes applied" if outcome.changed else "no changes needed"
        lines.append(f"Result: OK — {verdict}. Next: mfgctl doctor")
    return "\n".join(lines)
