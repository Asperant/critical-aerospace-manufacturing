"""WP-CORE-003 command idempotency and durable outcomes."""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0002_command_acceptance"
down_revision = "0001_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/manufacturing_core/migrations/0002_command_acceptance.sql"
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
        f"GRANT SELECT, INSERT ON TABLE core.command_idempotency TO {quoted}"
    )
    connection.exec_driver_sql(
        f"GRANT SELECT, INSERT ON TABLE core.command_outcome TO {quoted}"
    )


def downgrade() -> None:
    raise RuntimeError(
        "Core migrations are forward-only; restore from a controlled backup"
    )
