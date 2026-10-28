"""TEST-CICD-002-003: the digest-pinned deployment, decided against a fake host.

Preflight failures must roll nothing out; a failed rollout, health or smoke stage
must roll back to the last SUCCEEDED release when there is one, and the record
must say exactly what happened.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import pytest
from cap_release.deploy import DeployError, deploy, render_override
from cap_release.manifest import build_manifest, validate_manifest
from cap_release.registry import ImageRegistry, load_registry

COMMIT = "c" * 40
DIGEST = "sha256:" + "a" * 64
OLD_DIGEST = "sha256:" + "9" * 64


class FakeHost:
    def __init__(self, **overrides: Any) -> None:
        self.commit = COMMIT
        self.changes: list[str] = []
        self.on_main = True
        self.gate: str | Exception | None = "success"
        self.digests_present = True
        self.rollout_fails: list[int] = []  # 1-based rollout call numbers that fail
        self.bad_health: list[str] = []
        self.smoke_ok: bool | Exception = True
        self.migrate_error: str | None = None
        self.previous: tuple[dict[str, Any], dict[str, Any]] | None = None
        self.rollouts: list[str] = []
        self.migrations: list[str] = []
        self.saved: list[tuple[dict[str, Any], dict[str, Any]]] = []
        self.clock = dt.datetime(2026, 10, 28, 12, 0, tzinfo=dt.UTC)
        for key, value in overrides.items():
            setattr(self, key, value)

    def now(self) -> dt.datetime:
        self.clock += dt.timedelta(seconds=1)
        return self.clock

    def checked_out_commit(self) -> str:
        return self.commit

    def tree_changes(self) -> list[str]:
        return self.changes

    def commit_on_main(self, commit: str) -> bool:
        return self.on_main

    def ci_gate_conclusion(self, commit: str) -> str | None:
        if isinstance(self.gate, Exception):
            raise self.gate
        return self.gate

    def digest_in_registry(self, reference: str) -> bool:
        return self.digests_present

    def rollout(self, override: str) -> None:
        self.rollouts.append(override)
        if len(self.rollouts) in self.rollout_fails:
            raise DeployError("compose up failed")

    def unhealthy(self) -> list[str]:
        return self.bad_health

    def smoke(self) -> bool:
        if isinstance(self.smoke_ok, Exception):
            raise self.smoke_ok
        return self.smoke_ok

    def migrate(self, target: str) -> None:
        self.migrations.append(target)
        if self.migrate_error:
            raise DeployError(self.migrate_error)

    def last_succeeded(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        return self.previous

    def save(self, manifest: Any, record: Any) -> None:
        self.saved.append((dict(manifest), dict(record)))


def make_manifest(
    repo: Path, digest: str = DIGEST, commit: str = COMMIT, run: int = 5
) -> dict[str, Any]:
    return build_manifest(
        repo,
        load_registry(repo),
        {"mlflow": digest},
        commit=commit,
        run_id=run,
        run_attempt=1,
        run_url=f"https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/{run}",
        created_at=dt.datetime(2026, 10, 28, tzinfo=dt.UTC),
    )


def results(record: dict[str, Any]) -> dict[str, str]:
    return {s["stage"]: s["result"] for s in record["stages"]}


def test_the_override_pins_every_service_to_its_digest_and_never_builds(
    repo: Path,
) -> None:
    text = render_override(load_registry(repo), make_manifest(repo))
    assert (
        text.count(f"ghcr.io/asperant/cap-mlflow@{DIGEST}") == 2
    )  # mlflow and mlflow-init
    assert text.count("build: !reset null") == 2
    assert ":latest" not in text and "sha-" not in text


def test_the_override_refuses_a_manifest_that_lacks_a_registry_image(
    repo: Path,
) -> None:
    manifest = make_manifest(repo)
    manifest["service_images"] = []
    with pytest.raises(DeployError):
        render_override(load_registry(repo), manifest)


def test_a_clean_main_derived_release_is_deployed_and_recorded(repo: Path) -> None:
    host = FakeHost()
    outcome = deploy(make_manifest(repo), load_registry(repo), host)
    assert outcome.exit_code == 0 and outcome.record["result"] == "SUCCEEDED"
    assert results(outcome.record) == {
        "preflight": "PASSED",
        "migrate": "SKIPPED",
        "rollout": "PASSED",
        "health": "PASSED",
        "smoke": "PASSED",
    }
    assert len(host.rollouts) == 1 and host.migrations == []
    saved_manifest, saved_record = host.saved[0]
    assert (
        saved_record["manifest_sha256"]
        and saved_manifest["release_id"] == saved_record["release_id"]
    )
    assert saved_record["host_source"]["manual_patches"] == 0
    assert saved_record["supply_chain_verification"] == {
        "main_derived": True,
        "ci_gate": "success",
        "digests_in_registry": True,
        "tags_trusted": False,
    }


@pytest.mark.parametrize(
    ("host", "expect"),
    [
        (FakeHost(changes=[" M infra/compose/compose.yaml"]), "manual change"),
        (FakeHost(commit="d" * 40), "not the release commit"),
        (FakeHost(on_main=False), "not on main"),
        (FakeHost(gate="failure"), "ci-gate"),
        (FakeHost(gate=None), "ci-gate"),
        (FakeHost(digests_present=False), "digest not found"),
    ],
)
def test_a_failed_preflight_rolls_nothing_out(
    repo: Path, host: FakeHost, expect: str
) -> None:
    outcome = deploy(make_manifest(repo), load_registry(repo), host)
    assert outcome.exit_code == 1 and outcome.record["result"] == "FAILED"
    assert results(outcome.record) == {
        "preflight": "FAILED",
        "migrate": "NOT_RUN",
        "rollout": "NOT_RUN",
        "health": "NOT_RUN",
        "smoke": "NOT_RUN",
    }
    assert expect in outcome.record["stages"][0]["detail"]
    assert (
        host.rollouts == [] and host.saved
    ), "nothing rolled out, but the refusal is recorded"


def test_a_manifest_with_a_tag_identity_is_refused_at_preflight(repo: Path) -> None:
    manifest = make_manifest(repo)
    manifest["service_images"][0]["reference"] = "ghcr.io/asperant/cap-mlflow:latest"
    assert validate_manifest(manifest)
    host = FakeHost()
    outcome = deploy(manifest, load_registry(repo), host)
    assert outcome.record["result"] == "FAILED" and host.rollouts == []


def test_a_release_with_a_bound_schema_runs_the_migration_stage(repo: Path) -> None:
    manifest = make_manifest(repo)
    manifest["database_schema_target"] = {
        "state": "BOUND",
        "identity": "manufacturing-core:0007_lot_lineage",
    }
    host = FakeHost()
    outcome = deploy(manifest, load_registry(repo), host)
    assert host.migrations == ["manufacturing-core:0007_lot_lineage"]
    assert (
        results(outcome.record)["migrate"] == "PASSED"
        and outcome.record["result"] == "SUCCEEDED"
    )


def test_a_failed_migration_stops_before_any_rollout(repo: Path) -> None:
    manifest = make_manifest(repo)
    manifest["database_schema_target"] = {
        "state": "BOUND",
        "identity": "manufacturing-core:0007_lot_lineage",
    }
    host = FakeHost(migrate_error="lock timeout")
    outcome = deploy(manifest, load_registry(repo), host)
    assert results(outcome.record) == {
        "preflight": "PASSED",
        "migrate": "FAILED",
        "rollout": "NOT_RUN",
        "health": "NOT_RUN",
        "smoke": "NOT_RUN",
    }
    assert host.rollouts == [] and outcome.record["result"] == "FAILED"


@pytest.mark.parametrize(
    ("host", "failed", "not_run"),
    [
        (FakeHost(rollout_fails=[1]), "rollout", ["health", "smoke"]),
        (FakeHost(bad_health=["mlflow=starting"]), "health", ["smoke"]),
        (FakeHost(smoke_ok=False), "smoke", []),
    ],
)
def test_a_failed_stage_is_recorded_and_later_stages_do_not_run(
    repo: Path, host: FakeHost, failed: str, not_run: list[str]
) -> None:
    outcome = deploy(make_manifest(repo), load_registry(repo), host)
    got = results(outcome.record)
    assert got[failed] == "FAILED" and outcome.exit_code == 1
    assert all(got[name] == "NOT_RUN" for name in not_run)
    assert outcome.record["result"] == "FAILED" and outcome.record["rollback"] is None


def previous(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    old = make_manifest(repo, digest=OLD_DIGEST, commit="e" * 40, run=4)
    return {"release_id": old["release_id"], "result": "SUCCEEDED"}, old


@pytest.mark.parametrize(
    "host",
    [
        FakeHost(bad_health=["mlflow=starting"]),
        FakeHost(smoke_ok=False),
        FakeHost(rollout_fails=[1]),
    ],
)
def test_a_failed_release_rolls_back_to_the_last_succeeded_one(
    repo: Path, host: FakeHost
) -> None:
    host.previous = previous(repo)
    outcome = deploy(make_manifest(repo), load_registry(repo), host)
    record = outcome.record
    assert record["result"] == "ROLLED_BACK" and outcome.exit_code == 1
    assert record["rollback"] == {
        "to_release_id": host.previous[0]["release_id"],
        "result": "SUCCEEDED",
    }
    assert record["previous_release_id"] == host.previous[0]["release_id"]
    assert OLD_DIGEST in host.rollouts[-1] and DIGEST not in host.rollouts[-1]


def test_a_failed_rollback_is_recorded_as_failed_not_hidden(repo: Path) -> None:
    host = FakeHost(smoke_ok=False, rollout_fails=[2])
    host.previous = previous(repo)
    record = deploy(make_manifest(repo), load_registry(repo), host).record
    assert record["result"] == "FAILED"
    assert record["rollback"]["result"] == "FAILED"


def test_a_failed_preflight_never_rolls_back(repo: Path) -> None:
    host = FakeHost(gate="failure")
    host.previous = previous(repo)
    outcome = deploy(make_manifest(repo), load_registry(repo), host)
    assert host.rollouts == [] and outcome.record["rollback"] is None


def test_the_registry_is_not_trusted_without_images(repo: Path) -> None:
    host = FakeHost()
    manifest = make_manifest(repo)
    manifest["service_images"] = []
    outcome = deploy(manifest, ImageRegistry("ghcr.io/asperant", ()), host)
    assert outcome.record["result"] == "FAILED" and host.rollouts == []


def test_an_unreadable_ci_gate_is_reported_as_unreadable_not_as_missing(
    repo: Path,
) -> None:
    """A gh failure (for example an unwritable cache directory) must say so, and still deploy nothing."""
    host = FakeHost(gate=DeployError("mkdir /tmp/gh-cli-cache: permission denied"))
    outcome = deploy(make_manifest(repo), load_registry(repo), host)
    detail = outcome.record["stages"][0]["detail"]
    assert "could not be read" in detail and "permission denied" in detail
    assert outcome.record["supply_chain_verification"]["ci_gate"] == "unreadable"
    assert outcome.record["result"] == "FAILED" and host.rollouts == []


def test_a_failing_smoke_stage_keeps_the_reason_in_the_record(repo: Path) -> None:
    host = FakeHost(
        smoke_ok=DeployError("ImportError: No module named pytest_quarantine")
    )
    outcome = deploy(make_manifest(repo), load_registry(repo), host)
    smoke = outcome.record["stages"][4]
    assert smoke["result"] == "FAILED" and "pytest_quarantine" in smoke["detail"]
    assert outcome.record["result"] == "FAILED"
