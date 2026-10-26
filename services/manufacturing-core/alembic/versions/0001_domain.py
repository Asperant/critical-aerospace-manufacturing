"""Create the initial Core schema and record the migration ledger."""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0001_domain"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    source_path = (
        Path(__file__).parents[2] / "src/manufacturing_core/migrations/0001_domain.sql"
    )
    source = source_path.read_text(encoding="utf-8")
    op.execute(sa.text(source))
    digest = __import__("hashlib").sha256(source.encode()).hexdigest()
    runtime_role = op.get_context().opts.get("runtime_role")
    if not isinstance(runtime_role, str) or not runtime_role.strip():
        raise RuntimeError("explicit runtime role required for Core migration")
    op.execute(
        sa.text(
            "INSERT INTO core.schema_migration(version, sha256, runtime_role) "
            "VALUES (:version, :sha256, :runtime_role)"
        ),
        {"version": revision, "sha256": digest, "runtime_role": runtime_role},
    )
    connection = op.get_bind()
    quoted = connection.dialect.identifier_preparer.quote(runtime_role)
    connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA core TO {quoted}")
    for table in (
        "equipment",
        "manufacturing_route",
        "route_visit",
        "production_order",
        "lot",
        "serialized_component",
    ):
        connection.exec_driver_sql(
            f"GRANT SELECT, INSERT ON TABLE core.{connection.dialect.identifier_preparer.quote(table)} TO {quoted}"
        )


def downgrade() -> None:
    raise RuntimeError(
        "Core migrations are forward-only; restore from a controlled backup"
    )
