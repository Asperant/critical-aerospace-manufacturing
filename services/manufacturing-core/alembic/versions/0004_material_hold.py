"""WP-CORE-002 first-class material hold persistence."""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0004_material_hold"
down_revision = "0003_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/manufacturing_core/migrations/0004_material_hold.sql"
    )
    source = source_path.read_text(encoding="utf-8")
    connection = op.get_bind()
    for statement in source.split(";\n"):
        statement = statement.strip()
        if statement:
            connection.exec_driver_sql(statement)
    digest = __import__("hashlib").sha256(source.encode()).hexdigest()
    runtime_role = op.get_context().opts.get("runtime_role")
    if not isinstance(runtime_role, str) or not runtime_role.strip():
        raise RuntimeError("explicit runtime role required for Core migration")
    connection.execute(
        sa.text(
            "INSERT INTO core.schema_migration(version, sha256, runtime_role) "
            "VALUES (:version, :sha256, :runtime_role)"
        ),
        {"version": revision, "sha256": digest, "runtime_role": runtime_role},
    )
    quoted = connection.dialect.identifier_preparer.quote(runtime_role)
    connection.exec_driver_sql(
        "GRANT SELECT, INSERT ON TABLE core.material_hold TO " + quoted
    )
    connection.exec_driver_sql(
        "GRANT UPDATE(status, released_at, release_reason, released_command_id) "
        "ON TABLE core.material_hold TO " + quoted
    )
    # The entity and state revisions are the only canonical fields the runtime
    # transition surface may update; all other columns remain protected.
    for table, columns in (
        ("production_order", "revision"),
        ("lot", "revision"),
        ("serialized_component", "revision"),
        ("production_order_state", "revision, lifecycle_state"),
        ("lot_state", "revision, lifecycle_state, execution_state"),
        ("serialized_component_state", "revision, lifecycle_state, execution_state"),
    ):
        connection.exec_driver_sql(
            f"GRANT UPDATE({columns}) ON TABLE core.{connection.dialect.identifier_preparer.quote(table)} TO {quoted}"
        )


def downgrade() -> None:
    raise RuntimeError(
        "Core migrations are forward-only; restore from a controlled backup"
    )
