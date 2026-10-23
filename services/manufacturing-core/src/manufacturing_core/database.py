"""Explicit connections to an externally provisioned Core PostgreSQL database."""

import psycopg
from psycopg.rows import DictRow, dict_row


def require_restricted_role(conn: psycopg.Connection[DictRow], role: str) -> None:
    row = conn.execute(
        "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
        "FROM pg_catalog.pg_roles WHERE rolname = %s",
        (role,),
    ).fetchone()
    if row is None or any(row.values()):
        raise ValueError("Core role is missing or has administrative privileges")


def connect(dsn: str) -> psycopg.Connection[DictRow]:
    """No default credentials, implicit environment DSN or superuser fallback."""
    if not dsn.strip():
        raise ValueError("explicit Core DSN required")
    conn = psycopg.Connection[DictRow].connect(
        dsn, row_factory=dict_row, connect_timeout=10
    )
    try:
        if conn.info.server_version < 180000:
            raise ValueError("Core requires PostgreSQL 18 or newer")
        conn.execute("SET search_path TO pg_catalog")
        require_restricted_role(conn, conn.info.user)
        conn.commit()
    except Exception:
        conn.close()
        raise
    return conn


def connect_runtime(dsn: str) -> psycopg.Connection[DictRow]:
    conn = connect(dsn)
    try:
        row = conn.execute(
            "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner, "
            "pg_catalog.has_schema_privilege(current_user, oid, 'CREATE') AS ddl "
            "FROM pg_catalog.pg_namespace WHERE nspname = 'core'"
        ).fetchone()
        if row is None or row["ddl"] or row["owner"] == conn.info.user:
            raise ValueError(
                "runtime requires an existing separately owned Core schema"
            )
        membership = conn.execute(
            "SELECT pg_catalog.pg_has_role(current_user, %s, 'MEMBER') AS member",
            (row["owner"],),
        ).fetchone()
        if membership is None or membership["member"]:
            raise ValueError("runtime must not be a member of the migration role")
        conn.commit()
    except Exception:
        conn.close()
        raise
    return conn
