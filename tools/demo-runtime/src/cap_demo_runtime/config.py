from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    pg_dsn: str
    nats_url: str = "nats://nats:4222"
    world_id: str = "DEMO-WORLD"
    branch_id: str = "PRIMARY"
    stream: str = "CAP_EVENTS"
    subject: str = "cap.core.events"
    durable: str = "twin-primary"
    consumer_scope: str = "twin-primary"

    @classmethod
    def from_env(cls) -> "Settings":
        dsn = os.environ.get("CAP_PG_DSN", "").strip()
        if not dsn:
            host = os.environ.get("CAP_PG_HOST", "postgres").strip()
            user = os.environ.get("CAP_PG_USER", "cap").strip()
            password = os.environ.get("CAP_PG_PASSWORD", "").strip()
            database = os.environ.get("CAP_PG_DATABASE", "cap").strip()
            if not host or not user or not password or not database:
                raise ValueError("CAP_PG_DSN or complete CAP_PG_* settings required")
            dsn = f"postgresql://{user}:{password}@{host}:5432/{database}"
        values = {
            "nats_url": os.environ.get("CAP_NATS_URL", "nats://nats:4222"),
            "world_id": os.environ.get("CAP_WORLD_ID", "DEMO-WORLD"),
            "branch_id": os.environ.get("CAP_BRANCH_ID", "PRIMARY"),
            "stream": os.environ.get("CAP_EVENT_STREAM", "CAP_EVENTS"),
            "subject": os.environ.get("CAP_EVENT_SUBJECT", "cap.core.events"),
            "durable": os.environ.get("CAP_TWIN_DURABLE", "twin-primary"),
            "consumer_scope": os.environ.get(
                "CAP_TWIN_CONSUMER_SCOPE", "twin-primary"
            ),
        }
        if not all(isinstance(value, str) and value.strip() for value in values.values()):
            raise ValueError("runtime identity and transport settings must be nonblank")
        return cls(pg_dsn=dsn, **values)
