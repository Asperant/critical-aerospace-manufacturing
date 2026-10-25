"""TEST-EVT-001-005: version gate over verified compatibility results."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from cap_contracts import (
    CompatibilityResult,
    ContractDeclaration,
    ContractError,
    Deprecation,
    FileRef,
    Registry,
    compare_schema_files,
    compare_schemas,
    enforce_version_policy,
)


def comparison(*, breaking: bool) -> CompatibilityResult:
    before: dict[str, Any] = {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }
    after: dict[str, Any] = {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    }
    if breaking:
        after["properties"]["id"]["type"] = "integer"
    else:
        after["properties"]["note"] = {"type": "string"}
    return compare_schemas(before, after)


def test_breaking_same_major_is_rejected() -> None:
    result = comparison(breaking=True)
    assert result.breaking and not result.unverifiable
    with pytest.raises(ContractError) as caught:
        enforce_version_policy("core.order-query.v1", "core.order-query.v1", result)
    assert caught.value.code == "BREAKING_CHANGE_REQUIRES_MAJOR"


@pytest.mark.parametrize("major", [2, 4])
def test_breaking_higher_major_is_allowed(major: int) -> None:
    result = comparison(breaking=True)
    assert (
        enforce_version_policy(
            "core.order-query.v1", f"core.order-query.v{major}", result
        )
        is None
    )
    assert result.breaking  # Allowing a version does not reclassify the change.


def test_nonbreaking_same_major_is_allowed() -> None:
    result = comparison(breaking=False)
    assert result.compatible
    assert (
        enforce_version_policy("core.order-query.v1", "core.order-query.v1", result)
        is None
    )


@pytest.mark.parametrize(
    "result",
    [
        comparison(breaking=True),
        comparison(breaking=False),
        CompatibilityResult(unverifiable=("UNKNOWN",)),
    ],
)
def test_lower_major_rollback_is_rejected(result: CompatibilityResult) -> None:
    with pytest.raises(ContractError) as caught:
        enforce_version_policy("core.order-query.v2", "core.order-query.v1", result)
    assert caught.value.code == "VERSION_ROLLBACK"


@pytest.mark.parametrize("major", [1, 2])
@pytest.mark.parametrize(
    "unknown",
    [
        None,
        "UNKNOWN",
        {"compatible": True},
        CompatibilityResult(unverifiable=("UNKNOWN",)),
        CompatibilityResult(breaking=("field changed",), unverifiable=("ambiguous",)),
        CompatibilityResult(breaking=cast(Any, None)),
    ],
)
def test_unknown_or_ambiguous_result_fails_closed(major: int, unknown: object) -> None:
    with pytest.raises(ContractError) as caught:
        enforce_version_policy(
            "core.order-query.v1", f"core.order-query.v{major}", unknown
        )
    assert caught.value.code == "COMPATIBILITY_UNVERIFIABLE"


def test_unrelated_contract_family_is_rejected() -> None:
    with pytest.raises(ContractError) as caught:
        enforce_version_policy(
            "core.order-query.v1", "vision.order-query.v2", comparison(breaking=True)
        )
    assert caught.value.code == "CONTRACT_FAMILY_MISMATCH"


def declaration(
    major: int = 2, family: str = "core.order-query"
) -> ContractDeclaration:
    repo = Path(__file__).resolve().parents[2]
    base = ContractDeclaration.from_mapping(
        json.loads(
            (repo / "packages/contracts/registry/core.order-query.v1.json").read_text()
        )
    )
    return replace(base, contract_id=f"{family}.v{major}", version=major)


@pytest.mark.parametrize(
    "replacement", ["core.other-query.v3", "core.order-query.v2", "core.order-query.v1"]
)
def test_invalid_replacement_family_or_major_is_rejected(replacement: str) -> None:
    old = replace(declaration(), deprecation=Deprecation("DEPRECATED", replacement))
    major = int(replacement.rsplit("v", 1)[1])
    target = declaration(major, replacement.rsplit(".v", 1)[0])
    entries = {target.contract_id: target, old.contract_id: old}
    with pytest.raises(ContractError) as caught:
        Registry(entries)
    assert caught.value.code == "REPLACEMENT_NOT_LATER_MAJOR"


@pytest.mark.parametrize("major", [3, 5])
def test_later_same_family_replacement_remains_allowed(major: int) -> None:
    target = declaration(major)
    old = replace(
        declaration(), deprecation=Deprecation("DEPRECATED", target.contract_id)
    )
    assert (
        Registry({old.contract_id: old, target.contract_id: target}).get(
            old.contract_id
        )
        == old
    )


def test_missing_replacement_is_still_rejected() -> None:
    old = replace(
        declaration(), deprecation=Deprecation("DEPRECATED", "core.order-query.v3")
    )
    with pytest.raises(ContractError) as caught:
        Registry({old.contract_id: old})
    assert caught.value.code == "REPLACEMENT_UNKNOWN"


@pytest.mark.parametrize("failure", ["drift", "missing_reference", "cycle"])
def test_unverifiable_local_schema_cannot_be_approved_by_major_increase(
    tmp_path: Path, failure: str
) -> None:
    package = tmp_path / "packages/contracts"
    package.mkdir(parents=True)
    document = (
        {"type": "string"}
        if failure == "drift"
        else {"$ref": "#" if failure == "cycle" else "missing.json"}
    )
    raw = json.dumps(document).encode()
    path = package / "root.json"
    path.write_bytes(raw)
    ref = FileRef("packages/contracts/root.json", hashlib.sha256(raw).hexdigest())
    if failure == "drift":
        path.write_text('{"type":"integer"}')
    result = compare_schema_files(
        ref, ref, old_repo_root=tmp_path, new_repo_root=tmp_path
    )
    assert result.unverifiable
    if failure == "drift":
        assert all("SCHEMA_DRIFT" in reason for reason in result.unverifiable)
    with pytest.raises(ContractError) as caught:
        enforce_version_policy("core.order-query.v1", "core.order-query.v2", result)
    assert caught.value.code == "COMPATIBILITY_UNVERIFIABLE"
