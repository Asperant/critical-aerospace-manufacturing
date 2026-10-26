import pytest
from manufacturing_core.role_matrix import (
    SERVICE_SCHEMAS,
    SchemaRoleBinding,
    validate_role_map,
)


def bindings() -> dict[str, SchemaRoleBinding]:
    return {
        schema: SchemaRoleBinding(
            schema=schema,
            owner_role=f"{schema}_migration",
            runtime_role=f"{schema}_runtime",
        )
        for schema in SERVICE_SCHEMAS
    }


def test_role_matrix_requires_exact_service_schema_set() -> None:
    role_map = bindings()
    assert tuple(item.schema for item in validate_role_map(role_map)) == SERVICE_SCHEMAS
    role_map.pop("ai")
    with pytest.raises(ValueError, match="exactly"):
        validate_role_map(role_map)


def test_role_matrix_rejects_shared_runtime_or_migration_identity() -> None:
    role_map = bindings()
    role_map["twin"] = SchemaRoleBinding("twin", "twin_migration", "core_runtime")
    with pytest.raises(ValueError, match="distinct"):
        validate_role_map(role_map)
    role_map = bindings()
    role_map["ai"] = SchemaRoleBinding("ai", "ai_runtime", "ai_runtime")
    with pytest.raises(ValueError, match="differ"):
        validate_role_map(role_map)
