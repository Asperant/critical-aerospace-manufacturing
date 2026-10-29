from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import TypeAdapter, ValidationError
from psycopg.rows import dict_row

from manufacturing_core.commands import OperationalCommandV1, PlaceLotOnHold
from manufacturing_core.transitions import CoreTransitionService

from .config import Settings


def _connect(settings: Settings) -> psycopg.Connection[Any]:
    return psycopg.connect(settings.pg_dsn, row_factory=dict_row, connect_timeout=10)


def _event_id(connection: psycopg.Connection[Any], command_id: str) -> str | None:
    row = connection.execute(
        "SELECT event_id FROM core.outbox WHERE event->>'causation_id' = %s "
        "ORDER BY created_at DESC LIMIT 1",
        (command_id,),
    ).fetchone()
    return None if row is None else row["event_id"]


def create_app() -> FastAPI:
    settings = Settings.from_env()
    permissions = tuple(
        value.strip()
        for value in os.environ.get("CAP_CORE_PERMISSIONS", "core.lot.place_hold").split(",")
        if value.strip()
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        with _connect(settings) as connection:
            connection.execute("SELECT 1")
        return {"status": "UP", "service": "manufacturing-core", "world_id": settings.world_id}

    @app.post("/v1/commands")
    def command(body: dict[str, object]) -> dict[str, object]:
        try:
            parsed = TypeAdapter(OperationalCommandV1).validate_python(body)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail="command contract rejected") from exc
        if not isinstance(parsed, PlaceLotOnHold):
            raise HTTPException(status_code=501, detail="demo supports PlaceLotOnHold only")
        if parsed.world_id != settings.world_id:
            raise HTTPException(status_code=409, detail="world scope rejected")
        try:
            with _connect(settings) as connection:
                outcome = CoreTransitionService(connection).place_lot_on_hold(
                    permissions,
                    parsed,
                    expected_world_id=settings.world_id,
                )
                event_id = _event_id(connection, str(parsed.command_id))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail="Core authorization denied") from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Core database unavailable") from exc
        return {
            "command_id": str(outcome.command_id),
            "outcome_id": str(outcome.outcome_id),
            "status": outcome.status.value,
            "world_id": outcome.world_id,
            "correlation_id": outcome.correlation_id,
            "event_id": event_id,
            "effect_verification": outcome.effect_verification.value,
            "error_code": outcome.error_code,
            "detail": outcome.detail,
        }

    @app.get("/v1/lots/{lot_id}")
    def lot(lot_id: str) -> dict[str, object]:
        with _connect(settings) as connection:
            row = connection.execute(
                "SELECT l.id, l.revision, s.lifecycle_state, s.execution_state, "
                "EXISTS (SELECT 1 FROM core.material_hold h WHERE h.lot_id=l.id AND h.status='ACTIVE') AS held "
                "FROM core.lot l JOIN core.lot_state s ON s.id=l.id WHERE l.id=%s",
                (lot_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="lot not found")
        return {"world_id": settings.world_id, **dict(row)}

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("cap_demo_runtime.core_api:create_app", host="0.0.0.0", port=8081, factory=True)
