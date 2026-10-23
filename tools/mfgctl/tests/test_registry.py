from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from mfgctl import registry

EXAMPLE = Path(__file__).resolve().parents[1] / "schemas" / "capabilities.json"


def example() -> dict[str, Any]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def write(root: Path, data: Any) -> Path:
    path = root / registry.DEFAULT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_published_example_satisfies_the_loader(tmp_path: Path) -> None:
    write(tmp_path, example())
    loaded = registry.load(tmp_path, {})
    assert [p.name for p in loaded.profiles] == ["core", "full"]
    assert loaded.capability("platform").timeout_s == 120
    assert loaded.compose_args() == [
        "docker",
        "compose",
        "-f",
        "infra/compose/compose.yaml",
    ]


def test_missing_registry_explains_the_dependency(tmp_path: Path) -> None:
    with pytest.raises(registry.RegistryMissingError, match="WP-PLAT-001"):
        registry.load(tmp_path, {})


def test_override_path_is_relative_to_repository(tmp_path: Path) -> None:
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps(example()), encoding="utf-8")
    loaded = registry.load(tmp_path, {registry.ENV_VAR: "custom.json"})
    assert loaded.path == custom


def test_unreadable_json_is_invalid(tmp_path: Path) -> None:
    path = write(tmp_path, {})
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(registry.RegistryInvalidError, match="unreadable"):
        registry.load(tmp_path, {})


BREAKAGES = [
    ("wrong schema", lambda d: d.update(schema="other/v9"), "expected mfgctl"),
    ("extra key", lambda d: d.update(extra=1), "unexpected extra"),
    ("missing key", lambda d: d.pop("scenarios"), "missing scenarios"),
    ("escaping path", lambda d: d.update(compose_files=["../x.yaml"]), "relative path"),
    (
        "absolute path",
        lambda d: d.update(compose_files=["/etc/x.yaml"]),
        "relative path",
    ),
    ("no profiles", lambda d: d.update(profiles=[]), "at least one profile"),
    ("bad name", lambda d: d["profiles"][0].update(name="Core"), "does not match"),
    (
        "dup profile",
        lambda d: d["profiles"].append(dict(d["profiles"][0])),
        "duplicate core",
    ),
    ("bad owner", lambda d: d["capabilities"][0].update(owner="Mallory"), "owner"),
    (
        "unknown profile",
        lambda d: d["capabilities"][0].update(profile="gpu"),
        "not declared",
    ),
    ("empty smoke", lambda d: d["capabilities"][0].update(smoke=[]), "argv list"),
    (
        "shell string",
        lambda d: d["capabilities"][0].update(smoke="make test"),
        "argv list",
    ),
    ("bad timeout", lambda d: d["capabilities"][0].update(timeout_s=0), "timeout_s"),
    (
        "bool timeout",
        lambda d: d["capabilities"][0].update(timeout_s=True),
        "timeout_s",
    ),
    (
        "bad scenario id",
        lambda d: d["scenarios"][0].update(id="gs-01"),
        "does not match",
    ),
]


@pytest.mark.parametrize(
    ("label", "mutate", "message"), BREAKAGES, ids=[b[0] for b in BREAKAGES]
)
def test_contract_violations_are_rejected(
    tmp_path: Path, label: str, mutate: Any, message: str
) -> None:
    data = copy.deepcopy(example())
    mutate(data)
    write(tmp_path, data)
    with pytest.raises(registry.RegistryInvalidError, match=message):
        registry.load(tmp_path, {})


def test_unknown_names_list_the_known_ones(tmp_path: Path) -> None:
    write(tmp_path, example())
    loaded = registry.load(tmp_path, {})
    with pytest.raises(registry.UnknownNameError, match="known: core, full"):
        loaded.profile("gpu")
    with pytest.raises(registry.UnknownNameError, match="known: GS-01"):
        loaded.scenario("GS-99")
