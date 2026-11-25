"""Restricted runtime connection factory for service-owned PostgreSQL schemas."""

from psycopg import Connection
from psycopg.rows import DictRow, dict_row


def connect_runtime(dsn: str, *, application_name: str) -> Connection[DictRow]:
    if not dsn.strip() or not application_name.strip():
        raise ValueError("restricted runtime DSN and application name are required")
    return Connection[DictRow].connect(
        dsn, row_factory=dict_row, application_name=application_name
    )
