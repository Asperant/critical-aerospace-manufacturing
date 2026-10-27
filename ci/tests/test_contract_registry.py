"""TEST-EVT-001-001: contract registry layout, version rules and boundary validation.

Unit and contract level over the registered ``core.order-query.v1`` exemplar and
synthetic registries in temporary directories. No broker, envelope, command contract
or integration behaviour is involved, and nothing here certifies any readiness.
"""

import copy
import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from cap_contracts import (
    BoundaryValidator,
    ContractError,
    ContractViolation,
    Registry,
    is_successor,
    parse_contract_id,
)
from cap_contracts.registry import ContractDeclaration

REPO = Path(__file__).resolve().parents[2]
REGISTRY_DIR = REPO / "packages" / "contracts" / "registry"
EXEMPLAR = "core.order-query.v1"
CORE_V1 = Path("services/manufacturing-core/contracts/v1")
CORE_FILES = (
    "order-query-request.schema.json",
    "order-query.schema.json",
    "order-query.normal.json",
    "order-query.reentrant.json",
)
Record = dict[str, Any]
# A mutation is (operation, dotted path, value); list items use their index.
Mutation = tuple[str, str, object]


def exemplar_record() -> Record:
    record: Record = json.loads(
        (REGISTRY_DIR / f"{EXEMPLAR}.json").read_text(encoding="utf-8")
    )
    return record


def fixture(name: str) -> Record:
    value: Record = json.loads((REPO / CORE_V1 / name).read_text(encoding="utf-8"))
    return value


def apply(record: Record, mutation: Mutation) -> Record:
    """Return a deep copy of ``record`` with one set/pop applied at a dotted path."""
    result = copy.deepcopy(record)
    operation, dotted, value = mutation
    *parents, leaf = dotted.split(".")
    node: Any = result
    for part in parents:
        node = node[int(part)] if isinstance(node, list) else node[part]
    if operation == "set":
        if isinstance(node, list):
            node[int(leaf)] = value
        else:
            node[leaf] = value
    else:
        node.pop(leaf)
    return result


def repo_copy(tmp_path: Path) -> Path:
    """A throwaway repository root holding only the four exemplar producer files."""
    root = tmp_path / "repo"
    (root / CORE_V1).mkdir(parents=True)
    for name in CORE_FILES:
        shutil.copy(REPO / CORE_V1 / name, root / CORE_V1 / name)
    return root


def write_registry(directory: Path, records: list[Record]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for record in records:
        (directory / f"{record['contract_id']}.json").write_text(
            json.dumps(record), encoding="utf-8"
        )
    return directory


def successor_record(major: int, family: str = "core.order-query") -> Record:
    record = copy.deepcopy(exemplar_record())
    record["contract_id"] = f"{family}.v{major}"
    record["version"] = major
    return record


def deprecated(replacement: str, base: Record | None = None) -> Record:
    record = copy.deepcopy(base or exemplar_record())
    record["deprecation"] = {"status": "DEPRECATED", "replacement": replacement}
    return record


def error_code(call: Callable[[], object]) -> str:
    with pytest.raises(ContractError) as caught:
        call()
    return caught.value.code


def file_ref(path: Path, root: Path) -> Record:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


# --- identity and version rules --------------------------------------------------


@pytest.mark.parametrize(
    ("contract_id", "family", "major"),
    [
        ("core.order-query.v1", "core.order-query", 1),
        ("evt.lot-held.v12", "evt.lot-held", 12),
        ("a.b.v3", "a.b", 3),
    ],
)
def test_valid_contract_ids_parse(contract_id: str, family: str, major: int) -> None:
    parsed = parse_contract_id(contract_id)
    assert (parsed.family, parsed.major, parsed.contract_id) == (
        family,
        major,
        contract_id,
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "core.order-query",
        "core.order-query.v0",
        "core.order-query.v01",
        "core.order-query.V1",
        "Core.order-query.v1",
        "core.order-query.v1 ",
        " core.order-query.v1",
        "orderquery.v1",
        ".core.order-query.v1",
        "core..order-query.v1",
        "core.order_query.v1",
        "core.order-query.v-1",
        "core.order-query.v1.1",
        None,
        1,
        b"core.order-query.v1",
        ["core.order-query.v1"],
    ],
)
def test_invalid_contract_ids_are_rejected(value: object) -> None:
    assert error_code(lambda: parse_contract_id(value)) == "CONTRACT_ID_INVALID"


def test_successor_is_exactly_the_next_major_of_the_same_family() -> None:
    v1 = parse_contract_id("core.order-query.v1")
    assert is_successor(v1, parse_contract_id("core.order-query.v2"))
    assert not is_successor(v1, parse_contract_id("core.order-query.v3"))
    assert not is_successor(v1, parse_contract_id("core.order-query.v1"))
    assert not is_successor(parse_contract_id("core.order-query.v2"), v1)
    assert not is_successor(v1, parse_contract_id("core.other-query.v2"))


# --- declarations ----------------------------------------------------------------


def test_exemplar_declaration_loads_with_the_registered_metadata() -> None:
    declaration = ContractDeclaration.from_mapping(exemplar_record())
    assert declaration.contract_id == EXEMPLAR
    assert declaration.contract_type == "QUERY"
    assert declaration.canonical_producer == "manufacturing-core"
    assert declaration.semantic_owner == "Asrın Dündar"
    assert declaration.deprecation.status == "ACTIVE"
    assert declaration.input_schema is not None
    assert len(declaration.fixtures) == 2


EMPTY: list[str] = []
MALFORMED: list[tuple[Mutation, str]] = [
    (("pop", "canonical_producer", None), "FIELD_MISSING"),
    (("pop", "deprecation", None), "FIELD_MISSING"),
    (("set", "extra", "x"), "UNKNOWN_FIELD"),
    (("set", "contract_id", "core.order-query.v2"), "VERSION_MISMATCH"),
    (("set", "version", True), "VERSION_MISMATCH"),
    (("set", "version", "1"), "VERSION_MISMATCH"),
    (("set", "contract_id", "bad id"), "CONTRACT_ID_INVALID"),
    (("set", "contract_type", "TOPIC"), "CONTRACT_TYPE_INVALID"),
    (("set", "contract_type", "query"), "CONTRACT_TYPE_INVALID"),
    (("set", "sync_semantics", "BATCH"), "SYNC_SEMANTICS_INVALID"),
    (("set", "canonical_producer", ["a", "b"]), "PRODUCER_NOT_SINGULAR"),
    (("set", "canonical_producer", " "), "FIELD_INVALID"),
    (("set", "canonical_producer", " core "), "FIELD_INVALID"),
    (("set", "semantic_owner", ""), "FIELD_INVALID"),
    (("set", "purpose", 7), "FIELD_INVALID"),
    (("set", "declared_consumers", "Twin"), "CONSUMERS_INVALID"),
    (("set", "declared_consumers", ["Twin", "Twin"]), "CONSUMERS_INVALID"),
    (("set", "declared_consumers", [""]), "CONSUMERS_INVALID"),
    (("set", "fixtures", EMPTY), "FIXTURES_INVALID"),
    (("set", "fixtures.1", None), "FILE_REF_INVALID"),
    (("set", "output_schema.sha256", "abc"), "FILE_REF_INVALID"),
    (("set", "output_schema.sha256", "A" * 64), "FILE_REF_INVALID"),
    (("set", "output_schema.path", "/etc/passwd"), "FILE_REF_INVALID"),
    (("set", "output_schema.path", "../x.json"), "FILE_REF_INVALID"),
    (("set", "output_schema.path", "a//b.json"), "FILE_REF_INVALID"),
    (("set", "output_schema.path", "a\\b.json"), "FILE_REF_INVALID"),
    (("set", "output_schema.extra", "x"), "FILE_REF_INVALID"),
    (("set", "output_schema", "x.json"), "FILE_REF_INVALID"),
    (("set", "semantics", {"revision": 1}), "SEMANTICS_INVALID"),
    (("set", "deprecation", {"status": "ACTIVE"}), "DEPRECATION_INVALID"),
    (
        ("set", "deprecation", {"status": "RETIRED", "replacement": None}),
        "DEPRECATION_INVALID",
    ),
    (
        (
            "set",
            "deprecation",
            {"status": "ACTIVE", "replacement": "core.order-query.v2"},
        ),
        "DEPRECATION_INVALID",
    ),
    (
        ("set", "deprecation", {"status": "DEPRECATED", "replacement": None}),
        "DEPRECATION_INVALID",
    ),
    (
        ("set", "deprecation", {"status": "DEPRECATED", "replacement": "nope"}),
        "CONTRACT_ID_INVALID",
    ),
]


@pytest.mark.parametrize(("mutation", "code"), MALFORMED)
def test_malformed_declarations_are_rejected(mutation: Mutation, code: str) -> None:
    record = apply(exemplar_record(), mutation)
    assert error_code(lambda: ContractDeclaration.from_mapping(record)) == code


def test_duplicate_fixture_paths_are_rejected() -> None:
    record = exemplar_record()
    record["fixtures"] = [record["fixtures"][0], record["fixtures"][0]]
    assert (
        error_code(lambda: ContractDeclaration.from_mapping(record))
        == "FIXTURES_INVALID"
    )


@pytest.mark.parametrize("value", [None, [], "x", 1])
def test_non_object_declaration_is_rejected(value: object) -> None:
    assert (
        error_code(lambda: ContractDeclaration.from_mapping(value))
        == "DECLARATION_INVALID"
    )


# --- registry layout and cross-declaration rules ---------------------------------


def test_repository_registry_loads_and_verifies() -> None:
    registry = Registry.load(REGISTRY_DIR)
    assert registry.contract_ids() == (
        "ai.tool-interface.v1",
        "core.lot-dispatch-authorized.v1",
        "core.lot-held.v1",
        "core.lot-held.v2",
        "core.lot-operational-semantics.v1",
        "core.operational-command.v1",
        EXEMPLAR,
        "core.scheduling-snapshot.v1",
        "scheduler.recovery-plan.v1",
        "simulator.decision-request.v1",
        "simulator.dispatch-intake.v1",
        "simulator.dispatch-outcome.v1",
        "vision.inspection-observation.v1",
    )
    registry.verify(REPO)


def test_file_name_must_equal_the_contract_id(tmp_path: Path) -> None:
    directory = write_registry(tmp_path / "reg", [exemplar_record()])
    (directory / f"{EXEMPLAR}.json").rename(directory / "core.other-query.v1.json")
    assert error_code(lambda: Registry.load(directory)) == "FILE_NAME_MISMATCH"


def test_unexpected_registry_entries_are_rejected(tmp_path: Path) -> None:
    directory = write_registry(tmp_path / "reg", [exemplar_record()])
    (directory / "notes.txt").write_text("x", encoding="utf-8")
    assert error_code(lambda: Registry.load(directory)) == "REGISTRY_ENTRY_UNEXPECTED"
    (directory / "notes.txt").unlink()
    (directory / "sub").mkdir()
    assert error_code(lambda: Registry.load(directory)) == "REGISTRY_ENTRY_UNEXPECTED"


def test_readme_is_allowed_and_invalid_json_is_rejected(tmp_path: Path) -> None:
    directory = write_registry(tmp_path / "reg", [exemplar_record()])
    (directory / "README.md").write_text("# registry", encoding="utf-8")
    assert Registry.load(directory).contract_ids() == (EXEMPLAR,)
    (directory / "core.broken.v1.json").write_text("{not json", encoding="utf-8")
    assert error_code(lambda: Registry.load(directory)) == "DECLARATION_INVALID"


def test_unknown_contract_lookup_fails_closed() -> None:
    registry = Registry.load(REGISTRY_DIR)
    assert error_code(lambda: registry.get("core.missing.v1")) == "CONTRACT_UNKNOWN"
    assert registry.get(EXEMPLAR).contract_id == EXEMPLAR


def test_deprecation_replacement_may_be_any_later_major_that_exists(
    tmp_path: Path,
) -> None:
    ok = write_registry(
        tmp_path / "ok", [deprecated("core.order-query.v2"), successor_record(2)]
    )
    assert Registry.load(ok).contract_ids() == (EXEMPLAR, "core.order-query.v2")
    skip = write_registry(
        tmp_path / "skip", [deprecated("core.order-query.v3"), successor_record(3)]
    )
    assert (
        Registry.load(skip).get(EXEMPLAR).deprecation.replacement
        == "core.order-query.v3"
    )


def test_deprecation_replacement_must_exist(tmp_path: Path) -> None:
    missing = write_registry(tmp_path / "missing", [deprecated("core.order-query.v2")])
    assert error_code(lambda: Registry.load(missing)) == "REPLACEMENT_UNKNOWN"


def test_deprecation_replacement_must_be_a_later_major_of_the_same_family(
    tmp_path: Path,
) -> None:
    other = successor_record(2, family="core.other-query")
    wrong_family = write_registry(
        tmp_path / "family", [deprecated("core.other-query.v2"), other]
    )
    assert (
        error_code(lambda: Registry.load(wrong_family)) == "REPLACEMENT_NOT_LATER_MAJOR"
    )
    backwards = write_registry(
        tmp_path / "back",
        [exemplar_record(), deprecated(EXEMPLAR, successor_record(2))],
    )
    assert error_code(lambda: Registry.load(backwards)) == "REPLACEMENT_NOT_LATER_MAJOR"
    itself = write_registry(tmp_path / "self", [deprecated(EXEMPLAR)])
    assert error_code(lambda: Registry.load(itself)) == "REPLACEMENT_NOT_LATER_MAJOR"


# --- verification of referenced files --------------------------------------------


def test_verify_detects_schema_drift_and_missing_files(tmp_path: Path) -> None:
    root = repo_copy(tmp_path)
    registry = Registry.load(write_registry(tmp_path / "reg", [exemplar_record()]))
    registry.verify(root)
    schema = root / CORE_V1 / "order-query.schema.json"
    original = schema.read_text(encoding="utf-8")
    schema.write_text(original + "\n", encoding="utf-8")
    assert error_code(lambda: registry.verify(root)) == "SCHEMA_DRIFT"
    schema.unlink()
    assert error_code(lambda: registry.verify(root)) == "FILE_MISSING"
    schema.write_text(original, encoding="utf-8")
    registry.verify(root)


def test_verify_rejects_a_fixture_that_violates_its_schema(tmp_path: Path) -> None:
    root = repo_copy(tmp_path)
    bad = root / CORE_V1 / "order-query.bad.json"
    bad.write_text(json.dumps({"contract_version": EXEMPLAR}), encoding="utf-8")
    record = exemplar_record()
    record["fixtures"] = [file_ref(bad, root)]
    registry = Registry.load(write_registry(tmp_path / "reg", [record]))
    assert error_code(lambda: registry.verify(root)) == "FIXTURE_INVALID"


def test_verify_rejects_a_fixture_that_is_not_json(tmp_path: Path) -> None:
    root = repo_copy(tmp_path)
    bad = root / CORE_V1 / "order-query.bad.json"
    bad.write_text("{not json", encoding="utf-8")
    record = exemplar_record()
    record["fixtures"] = [file_ref(bad, root)]
    registry = Registry.load(write_registry(tmp_path / "reg", [record]))
    assert error_code(lambda: registry.verify(root)) == "FIXTURE_INVALID"


def test_verify_rejects_an_invalid_or_non_object_schema(tmp_path: Path) -> None:
    root = repo_copy(tmp_path)
    for index, content in enumerate(
        (json.dumps({"type": "nonsense"}), "[]", "{not json")
    ):
        broken = root / CORE_V1 / f"broken{index}.schema.json"
        broken.write_text(content, encoding="utf-8")
        record = exemplar_record()
        record["output_schema"] = file_ref(broken, root)
        registry = Registry.load(write_registry(tmp_path / f"reg{index}", [record]))
        assert error_code(lambda reg=registry: reg.verify(root)) == "SCHEMA_INVALID"


def test_verify_rejects_a_path_that_escapes_the_repository_root(tmp_path: Path) -> None:
    root = repo_copy(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (root / "link.json").symlink_to(outside)
    record = exemplar_record()
    record["output_schema"] = {
        "path": "link.json",
        "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
    }
    registry = Registry.load(write_registry(tmp_path / "reg", [record]))
    assert error_code(lambda: registry.verify(root)) == "FILE_REF_ESCAPES_ROOT"


# --- boundary validation ---------------------------------------------------------


def validator() -> BoundaryValidator:
    return BoundaryValidator(Registry.load(REGISTRY_DIR).get(EXEMPLAR), REPO)


@pytest.mark.parametrize("role", ["producer", "consumer"])
@pytest.mark.parametrize(
    "name", ["order-query.normal.json", "order-query.reentrant.json"]
)
def test_published_fixtures_pass_at_both_boundaries(role: str, name: str) -> None:
    validator().validate(fixture(name), role=role)


@pytest.mark.parametrize("role", ["producer", "consumer"])
def test_valid_request_passes_and_invalid_requests_fail(role: str) -> None:
    boundary = validator()
    boundary.validate_request(
        {"contract_version": EXEMPLAR, "order_id": "O-1"}, role=role
    )
    invalid: list[Record] = [
        {},
        {"contract_version": EXEMPLAR},
        {"contract_version": "core.order-query.v2", "order_id": "O-1"},
        {"contract_version": EXEMPLAR, "order_id": "  "},
        {"contract_version": EXEMPLAR, "order_id": "O-1", "extra": 1},
        {"contract_version": EXEMPLAR, "order_id": 5},
    ]
    for request in invalid:
        with pytest.raises(ContractViolation) as caught:
            boundary.validate_request(request, role=role)
        assert caught.value.code == "SCHEMA_VIOLATION"
        assert caught.value.role == role


def violation_of(mutation: Mutation, role: str = "consumer") -> ContractViolation:
    payload = apply(fixture("order-query.normal.json"), mutation)
    with pytest.raises(ContractViolation) as caught:
        validator().validate(payload, role=role)
    return caught.value


@pytest.mark.parametrize(
    ("mutation", "path"),
    [
        (("pop", "order", None), "/ [required]"),
        (("pop", "contract_version", None), "/ [required]"),
        (("set", "unexpected", 1), "/ [additionalProperties]"),
        (
            ("set", "contract_version", "core.order-query.v2"),
            "/contract_version [const]",
        ),
        (("pop", "order.revision", None), "/order [required]"),
        (("set", "order.revision", ""), "/order/revision [pattern]"),
        (("set", "order.revision", 3), "/order/revision [type]"),
        (("set", "lots.0.extra", "x"), "/lots/0 [additionalProperties]"),
        (("set", "lots", "none"), "/lots [type]"),
    ],
)
def test_payload_violations_name_the_path_and_keyword(
    mutation: Mutation, path: str
) -> None:
    violation = violation_of(mutation)
    assert path in violation.violations
    assert violation.contract_id == EXEMPLAR
    assert violation.role == "consumer"


def test_producer_role_is_reported_on_a_producer_violation() -> None:
    assert violation_of(("pop", "order", None), role="producer").role == "producer"


def test_violations_never_disclose_payload_values() -> None:
    secret = "SECRET-VALUE-9f3a"
    payload = fixture("order-query.normal.json")
    payload["order"]["revision"] = 7
    payload[secret] = secret
    with pytest.raises(ContractViolation) as caught:
        validator().validate(payload, role="consumer")
    assert secret not in str(caught.value)
    assert all(secret not in item for item in caught.value.violations)


def test_reported_violations_are_bounded_and_deduplicated() -> None:
    payload = fixture("order-query.normal.json")
    for index in range(60):
        payload[f"x{index}"] = index
    with pytest.raises(ContractViolation) as caught:
        validator().validate(payload, role="consumer")
    assert len(caught.value.violations) <= 20
    assert len(set(caught.value.violations)) == len(caught.value.violations)


@pytest.mark.parametrize("role", ["", "admin", "PRODUCER"])
def test_unknown_role_fails_closed(role: str) -> None:
    boundary = validator()
    payload = fixture("order-query.normal.json")
    assert (
        error_code(lambda: boundary.validate(payload, role=role))
        == "BOUNDARY_ROLE_INVALID"
    )
    request = {"contract_version": EXEMPLAR, "order_id": "O-1"}
    assert (
        error_code(lambda: boundary.validate_request(request, role=role))
        == "BOUNDARY_ROLE_INVALID"
    )


def test_contract_without_an_input_schema_fails_closed_for_requests() -> None:
    record = exemplar_record()
    del record["input_schema"]
    boundary = BoundaryValidator(ContractDeclaration.from_mapping(record), REPO)
    assert (
        error_code(lambda: boundary.validate_request({}, role="producer"))
        == "NO_INPUT_SCHEMA"
    )
    boundary.validate(fixture("order-query.normal.json"), role="producer")


def test_validator_construction_fails_closed_on_drift(tmp_path: Path) -> None:
    root = repo_copy(tmp_path)
    declaration = Registry.load(REGISTRY_DIR).get(EXEMPLAR)
    BoundaryValidator(declaration, root)
    schema = root / CORE_V1 / "order-query.schema.json"
    schema.write_text(schema.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert error_code(lambda: BoundaryValidator(declaration, root)) == "SCHEMA_DRIFT"
