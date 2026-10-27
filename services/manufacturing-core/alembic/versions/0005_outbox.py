"""WP-CORE-005 transactional outbox and lot event sequence."""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0005_outbox"
down_revision = "0004_material_hold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source_path = (
        Path(__file__).parents[2] / "src/manufacturing_core/migrations/0005_outbox.sql"
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
        f"GRANT SELECT, INSERT, UPDATE ON TABLE core.lot_event_sequence TO {quoted}"
    )
    connection.exec_driver_sql(f"GRANT SELECT, INSERT ON TABLE core.outbox TO {quoted}")
    connection.exec_driver_sql(
        f"GRANT UPDATE(publication_status, attempt_count, last_error) "
        f"ON TABLE core.outbox TO {quoted}"
    )


def downgrade() -> None:
    raise RuntimeError(
        "Core migrations are forward-only; restore from a controlled backup"
    )
