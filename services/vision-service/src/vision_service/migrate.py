"""Install the Vision outbox and shared processed-message ledger."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

from cap_event_consumer.migrate import migrate as migrate_consumer
from cap_event_consumer.migrate import migrate_owned_schema

VERSION = "0001_inspection_observation_outbox"
VISION_SCHEMA = "vision"
CONSUMER_SCHEMA = "vision_consumer"


def migrate(connection: Any, runtime_role: str) -> bool:
    """Stage both migrations in the caller-owned transaction."""
    consumer_changed = migrate_consumer(connection, CONSUMER_SCHEMA, runtime_role)
    source = (
        files("vision_service")
        .joinpath("migrations/0001_inspection_observation_outbox.sql")
        .read_text(encoding="utf-8")
    )
    vision_changed = migrate_owned_schema(
        connection,
        VISION_SCHEMA,
        runtime_role,
        VERSION,
        source,
        "inspection_observation_outbox",
        update_columns=(
            "published_at",
            "attempt_count",
            "claim_token",
            "claimed_until",
        ),
    )
    return consumer_changed or vision_changed
