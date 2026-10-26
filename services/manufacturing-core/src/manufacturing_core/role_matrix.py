"""Explicit, fail-closed PostgreSQL schema ownership contract.

The matrix describes role *bindings*, not credentials. Deployments must supply
the actual role names; this module never creates roles or invents identities.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

SERVICE_SCHEMAS = ("core", "twin", "automation", "ai")


@dataclass(frozen=True)
class SchemaRoleBinding:
    schema: str
    owner_role: str
    runtime_role: str


def validate_role_map(
    role_map: Mapping[str, SchemaRoleBinding],
) -> tuple[SchemaRoleBinding, ...]:
    """Validate a complete binding set before any SQL is executed."""
    if set(role_map) != set(SERVICE_SCHEMAS):
        raise ValueError("role map must bind exactly core, twin, automation and ai")
    bindings = tuple(role_map[schema] for schema in SERVICE_SCHEMAS)
    for binding in bindings:
        if binding.schema not in SERVICE_SCHEMAS:
            raise ValueError("unknown service schema")
        if not binding.owner_role.strip() or not binding.runtime_role.strip():
            raise ValueError("role names must be explicit and non-empty")
        if binding.owner_role == binding.runtime_role:
            raise ValueError("migration/owner and runtime roles must differ")
    if len({binding.runtime_role for binding in bindings}) != len(bindings):
        raise ValueError("runtime roles must be distinct per service schema")
    return bindings


def apply_role_matrix(conn, role_map: Mapping[str, SchemaRoleBinding]) -> None:
    """Apply only explicit same-schema grants; fail before partial application.

    Roles and schemas must already exist and be owned by the declared owner
    role. Cross-schema grants are deliberately never generated.
    """
    from psycopg import sql

    bindings = validate_role_map(role_map)
    for binding in bindings:
        role = conn.execute(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
            "rolbypassrls FROM pg_catalog.pg_roles WHERE rolname IN (%s, %s)",
            (binding.owner_role, binding.runtime_role),
        ).fetchall()
        if len(role) != 2 or any(any(row.values()) for row in role):
            raise ValueError(
                f"restricted roles missing or administrative: {binding.schema}"
            )
        schema = conn.execute(
            "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner "
            "FROM pg_catalog.pg_namespace WHERE nspname = %s",
            (binding.schema,),
        ).fetchone()
        if schema is None or schema["owner"] != binding.owner_role:
            raise ValueError(f"schema owner mismatch: {binding.schema}")
    for binding in bindings:
        conn.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(binding.schema), sql.Identifier(binding.runtime_role)
            )
        )
        conn.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA {} "
                "GRANT SELECT, INSERT ON TABLES TO {}"
            ).format(
                sql.Identifier(binding.owner_role),
                sql.Identifier(binding.schema),
                sql.Identifier(binding.runtime_role),
            )
        )
