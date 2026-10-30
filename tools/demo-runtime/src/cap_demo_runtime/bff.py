from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

import nats
import psycopg
from fastapi import Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from operations_bff.api import Session, correlation_id_of
from operations_bff.composition import RuntimeSettings, build_app
from operations_bff.config import CookieSettings, LoginConfig, SessionConfig
from operations_bff.facility_state import (
    TWIN_SOURCE,
    EquipmentState,
    FacilityStateReader,
    FacilityStateService,
    FacilityStateSnapshot,
    LotState,
    RoutePosition,
)
from operations_bff.oidc import OidcSettings
from operations_bff.overview import (
    AttentionFact,
    OverviewQuery,
    OverviewService,
    SourceSnapshot,
)
from psycopg.rows import DictRow, dict_row

from .config import Settings


def _connection(settings: Settings) -> psycopg.Connection[DictRow]:
    return psycopg.Connection[DictRow].connect(
        settings.pg_dsn, row_factory=dict_row, connect_timeout=10
    )


def _core_showcase(settings: Settings, world_id: str, lot_id: str) -> dict[str, Any]:
    url = (
        f"{settings.core_url.rstrip('/')}/v1/showcase/{quote(lot_id, safe='')}"
        f"?world_id={quote(world_id, safe='')}"
    )
    with urlopen(url, timeout=5) as response:  # noqa: S310 - configured internal demo boundary
        if response.status != 200:
            raise RuntimeError(f"Core showcase query returned HTTP {response.status}")
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise RuntimeError("Core showcase query returned a non-object")
    return value


def _http_health(url: str) -> dict[str, Any]:
    """Probe a configured internal HTTP health/readiness resource."""
    try:
        with urlopen(url, timeout=3) as response:  # noqa: S310 - configured demo boundary
            return {
                "status": "UP" if 200 <= response.status < 300 else "DEGRADED",
                "detail": f"HTTP {response.status}",
            }
    except Exception as exc:  # noqa: BLE001 - health must report dependency failures
        return {"status": "DOWN", "detail": f"{type(exc).__name__}: {exc}"}


async def _jetstream_health(settings: Settings) -> dict[str, Any]:
    connection = None
    try:
        connection = await nats.connect(settings.nats_url, connect_timeout=3)
        jetstream = connection.jetstream()
        stream = await jetstream.stream_info(settings.stream)
        consumer = await jetstream.consumer_info(settings.stream, settings.durable)
        delivered = consumer.delivered
        return {
            "status": "UP",
            "detail": f"{settings.stream}/{settings.durable} connected",
            "stream": stream.config.name,
            "messages": stream.state.messages,
            "consumer": consumer.name,
            "consumer_sequence": None if delivered is None else delivered.consumer_seq,
            "stream_sequence": None if delivered is None else delivered.stream_seq,
            "num_ack_pending": consumer.num_ack_pending,
            "num_redelivered": consumer.num_redelivered,
        }
    except Exception as exc:  # noqa: BLE001 - health must report dependency failures
        return {"status": "DOWN", "detail": f"{type(exc).__name__}: {exc}"}
    finally:
        if connection is not None:
            await connection.drain()


def _jetstream_health_sync(settings: Settings) -> dict[str, Any]:
    try:
        return asyncio.run(_jetstream_health(settings))
    except Exception as exc:  # noqa: BLE001 - health must report event-loop failures
        return {"status": "DOWN", "detail": f"{type(exc).__name__}: {exc}"}


def _health_item(
    component_id: str, label: str, status: str, detail: str, **fields: Any
) -> dict[str, Any]:
    return {
        "id": component_id,
        "label": label,
        "status": status,
        "detail": detail,
        **fields,
    }


def _system_observability(
    settings: Settings,
    world_id: str,
    lot_id: str,
    core: dict[str, Any],
    applied: dict[str, Any] | None,
    revision: dict[str, Any] | None,
) -> dict[str, Any]:
    hold = core.get("hold_command")
    outbox = core.get("outbox")
    dispatch = core.get("dispatch_attempt")
    jetstream = _jetstream_health_sync(settings)

    try:
        with _connection(settings) as connection:
            connection.execute("SELECT 1").fetchone()
            twin_update_count = connection.execute(
                "SELECT count(*) AS count FROM twin.applied_event "
                "WHERE world_id=%s AND consumer_scope=%s",
                (world_id, settings.consumer_scope),
            ).fetchone()["count"]
        postgres = _health_item(
            "postgresql", "PostgreSQL", "UP", "authenticated read completed"
        )
    except Exception as exc:  # noqa: BLE001 - expose a truthful degraded view
        postgres = _health_item(
            "postgresql", "PostgreSQL", "DOWN", f"{type(exc).__name__}: {exc}"
        )
        twin_update_count = None

    core_observability = core.get("observability", {})
    command_count = core_observability.get("commands")
    published_count = core_observability.get("published_events")
    active_hold_count = core_observability.get("active_holds")

    core_health = _http_health(f"{settings.core_url.rstrip('/')}/healthz")
    keycloak_health = _http_health(
        f"{os.environ.get('OPERATIONS_BFF_OIDC_ISSUER', '').rstrip('/')}/.well-known/openid-configuration"
    )
    twin_status = "UP" if revision is not None else "UNKNOWN"
    twin_detail = (
        f"projection {revision['status']} at {revision['source_event_id']}"
        if revision is not None
        else "no projection revision reported"
    )
    causation_id = None if hold is None else hold.get("causation_id")
    simulator_status = "OBSERVED" if causation_id else "UNKNOWN"
    simulator_detail = (
        f"causation {causation_id}"
        if causation_id
        else "no simulator causation reference reported"
    )
    architecture = [
        _health_item("simulator", "Simulator", simulator_status, simulator_detail),
        _health_item(
            "core",
            "Core",
            "REPORTED" if hold is not None else "NO_EVENT",
            "command outcome read through the internal Core boundary"
            if hold is not None
            else "no hold command outcome reported",
            command_id=None if hold is None else str(hold["command_id"]),
        ),
        _health_item(
            "postgresql",
            "PostgreSQL",
            "READ" if postgres["status"] == "UP" else "UNAVAILABLE",
            postgres["detail"],
        ),
        _health_item(
            "outbox",
            "Transactional Outbox",
            "PUBLISHED"
            if outbox and outbox.get("publication_status") == "PUBLISHED"
            else ("PENDING" if outbox is not None else "NOT_REPORTED"),
            "Core event intent is published"
            if outbox and outbox.get("publication_status") == "PUBLISHED"
            else "Core has not reported a published event for this lot",
            outbox_id=None if outbox is None else outbox.get("outbox_id"),
            event_id=None if outbox is None else outbox.get("event_id"),
        ),
        _health_item(
            "nats",
            "NATS / JetStream",
            "CONNECTED" if jetstream["status"] == "UP" else "UNAVAILABLE",
            jetstream["detail"],
            consumer=jetstream.get("consumer"),
            messages=jetstream.get("messages"),
        ),
        _health_item(
            "twin",
            "Digital Twin",
            "UPDATED" if applied else twin_status,
            twin_detail,
            source_event_id=None
            if revision is None
            else revision.get("source_event_id"),
        ),
        _health_item(
            "bff",
            "BFF",
            "SERVING",
            "authenticated showcase read model is serving this response",
        ),
    ]
    health = [
        postgres,
        _health_item("core", "Core", core_health["status"], core_health["detail"]),
        _health_item(
            "nats", "NATS / JetStream", jetstream["status"], jetstream["detail"]
        ),
        _health_item("digital-twin", "Digital Twin", twin_status, twin_detail),
        _health_item("bff", "BFF", "UP", "current authenticated response is serving"),
        _health_item(
            "keycloak", "Keycloak", keycloak_health["status"], keycloak_health["detail"]
        ),
    ]
    return {
        "architecture": architecture,
        "health": health,
        "counters": [
            {"id": "commands", "label": "Commands observed", "value": command_count},
            {
                "id": "published-events",
                "label": "Events published",
                "value": published_count,
            },
            {"id": "twin-updates", "label": "Twin updates", "value": twin_update_count},
            {"id": "active-holds", "label": "Active holds", "value": active_hold_count},
            {
                "id": "jetstream-messages",
                "label": "JetStream messages",
                "value": jetstream.get("messages"),
            },
        ],
        "selected_lot": lot_id,
        "world_id": world_id,
        "dispatch_status": None if dispatch is None else dispatch.get("status"),
    }


class TwinReader(FacilityStateReader):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def name(self) -> str:
        return TWIN_SOURCE

    def _rows(self) -> tuple[dict[str, Any], ...]:
        with _connection(self.settings) as connection:
            return tuple(
                connection.execute(
                    "SELECT state, aggregate_id, aggregate_version, source_revision "
                    "FROM twin.projection_entity WHERE world_id=%s AND branch_id=%s "
                    "ORDER BY aggregate_type, aggregate_id",
                    (self.settings.world_id, self.settings.branch_id),
                ).fetchall()
            )

    def _revision(self) -> tuple[str, str]:
        with _connection(self.settings) as connection:
            row = connection.execute(
                "SELECT source_event_id, status FROM twin.projection_revision "
                "WHERE world_id=%s AND branch_id=%s",
                (self.settings.world_id, self.settings.branch_id),
            ).fetchone()
        if row is None:
            raise RuntimeError("Twin projection has no revision")
        return row["source_event_id"], row["status"]

    def read(self, query: Any) -> FacilityStateSnapshot:
        revision, freshness = self._revision()
        lots: list[LotState] = []
        equipment: list[EquipmentState] = []
        for row in self._rows():
            state = row["state"]
            if state.get("aggregate_type") != "Lot":
                continue
            lots.append(
                LotState(
                    lot_id=row["aggregate_id"],
                    revision=str(row["aggregate_version"]),
                    lifecycle_state=str(state.get("lifecycle", "OBSERVED")),
                    execution_state="READY",
                    hold_state="ACTIVE" if state.get("hold_id") else "NONE",
                    route_position=RoutePosition(
                        route_id="DEMO-ROUTE",
                        visit_id="DEMO-VISIT-1",
                        position=0,
                        operation_class_id="ROUGH-MACHINING",
                    ),
                    epistemic_class=str(state.get("epistemic_class", "OBSERVED")),
                    freshness=freshness,
                )
            )
        return FacilityStateSnapshot(
            source=TWIN_SOURCE,
            revision=revision,
            as_of=datetime.now(UTC),
            freshness=freshness,
            equipment=tuple(equipment),
            lots=tuple(lots),
        )

    def read_overview(self, query: OverviewQuery) -> SourceSnapshot:
        revision, freshness = self._revision()
        facts = tuple(
            AttentionFact(
                item_id=f"hold/{row['aggregate_id']}",
                kind="QUALITY_EXCURSION",
                epistemic_class=str(row["state"].get("epistemic_class", "OBSERVED")),
                subject_type="Lot",
                subject_id=row["aggregate_id"],
                summary=str(row["state"].get("hold_reason", "Material hold active")),
            )
            for row in self._rows()
            if row["state"].get("hold_id")
        )
        return SourceSnapshot(
            source=TWIN_SOURCE,
            revision=revision,
            as_of=datetime.now(UTC),
            freshness=freshness,
            items=facts,
        )


class OverviewReader:
    name = TWIN_SOURCE

    def __init__(self, reader: TwinReader) -> None:
        self.reader = reader

    def read(self, query: OverviewQuery) -> SourceSnapshot:
        return self.reader.read_overview(query)


def create_app():
    settings = Settings.from_env()
    environment = "demo"
    oidc = OidcSettings(
        issuer=os.environ["OPERATIONS_BFF_OIDC_ISSUER"],
        client_id=os.environ["OPERATIONS_BFF_OIDC_CLIENT_ID"],
        redirect_uri=os.environ["OPERATIONS_BFF_OIDC_REDIRECT_URI"],
        environment_id=environment,
        client_secret=os.environ.get("OPERATIONS_BFF_OIDC_CLIENT_SECRET") or None,
        allow_insecure_http=os.environ.get("OPERATIONS_BFF_OIDC_ALLOW_INSECURE_HTTP")
        == "1",
        browser_issuer=os.environ.get("OPERATIONS_BFF_OIDC_BROWSER_ISSUER") or None,
        redirect_uris=tuple(
            os.environ.get("OPERATIONS_BFF_OIDC_REDIRECT_URIS", "").split()
        ),
        browser_issuers=tuple(
            os.environ.get("OPERATIONS_BFF_OIDC_BROWSER_ISSUERS", "").split()
        ),
    )
    runtime = RuntimeSettings(
        oidc=oidc,
        cookie=CookieSettings(same_site="lax"),
        session=SessionConfig(),
        login=LoginConfig(),
        post_login_path="/",
    )
    reader = TwinReader(settings)
    app = build_app(
        runtime,
        overview=OverviewService(OverviewReader(reader)),
        facility_state=FacilityStateService(reader),
    )

    @app.get("/v1/showcase", operation_id="getShowcase")
    def get_showcase(
        request: Request,
        auth: Session,
        world_id: str = Query(min_length=1, pattern=r"\S"),
        lot_id: str = Query("DEMO-LOT-001", min_length=1, pattern=r"\S"),
    ) -> JSONResponse:
        del auth
        if world_id != settings.world_id:
            return JSONResponse(
                {
                    "error_code": "WORLD_SCOPE_REJECTED",
                    "message": "world scope rejected",
                },
                status_code=409,
            )
        core = _core_showcase(settings, world_id, lot_id)
        with _connection(settings) as connection:
            applied = connection.execute(
                "SELECT event_id, applied_at FROM twin.applied_event "
                "WHERE consumer_scope=%s AND aggregate_id=%s AND world_id=%s "
                "ORDER BY applied_at DESC LIMIT 1",
                (settings.consumer_scope, lot_id, world_id),
            ).fetchone()
            revision = connection.execute(
                "SELECT source_event_id, status, updated_at FROM twin.projection_revision "
                "WHERE world_id=%s AND branch_id=%s",
                (world_id, settings.branch_id),
            ).fetchone()

        hold = core.get("hold_command")
        dispatch = core.get("dispatch_attempt")
        outbox = core.get("outbox")
        timeline: list[dict[str, Any]] = []
        if hold is not None and hold.get("causation_id"):
            timeline.append(
                {
                    "id": f"simulator-{hold['causation_id']}",
                    "kind": "SIMULATOR_TRIGGER",
                    "label": "Simulator quality event observed",
                    "status": "OBSERVED",
                    "source": "manufacturing-simulator → Core command boundary",
                    "occurred_at": hold.get("created_at"),
                    "event_ref": hold["causation_id"],
                }
            )
        if hold is not None and hold.get("status") == "ACCEPTED":
            timeline.append(
                {
                    "id": f"command-{hold['command_id']}",
                    "kind": "COMMAND_ACCEPTED",
                    "label": "Core hold command accepted",
                    "status": "ACCEPTED",
                    "source": "manufacturing-core",
                    "occurred_at": hold.get("created_at"),
                    "command_id": str(hold["command_id"]),
                    "event_ref": hold.get("causation_id"),
                }
            )
        if outbox is not None and outbox.get("publication_status") == "PUBLISHED":
            timeline.append(
                {
                    "id": f"outbox-{outbox['outbox_id']}",
                    "kind": "EVENT_PUBLISHED",
                    "label": "Hold event published",
                    "status": "PUBLISHED",
                    "source": "core.outbox → NATS/JetStream",
                    "occurred_at": outbox.get("created_at"),
                    "event_id": outbox.get("event_id"),
                    "outbox_id": outbox.get("outbox_id"),
                }
            )
        if applied is not None:
            timeline.append(
                {
                    "id": f"twin-{applied['event_id']}",
                    "kind": "TWIN_UPDATED",
                    "label": "Digital Twin projection updated",
                    "status": "FRESH"
                    if revision and revision["status"] == "FRESH"
                    else "STALE",
                    "source": "digital-twin-service",
                    "occurred_at": applied.get("applied_at"),
                    "event_id": applied.get("event_id"),
                }
            )
        if dispatch is not None:
            timeline.append(
                {
                    "id": f"dispatch-{dispatch['command_id']}",
                    "kind": "DISPATCH_BLOCKED",
                    "label": "Dispatch blocked — active quality hold",
                    "status": dispatch.get("error_code") or dispatch.get("status"),
                    "source": "manufacturing-core",
                    "occurred_at": dispatch.get("created_at"),
                    "command_id": str(dispatch["command_id"]),
                    "error_code": dispatch.get("error_code"),
                }
            )
        observability = _system_observability(
            settings, world_id, lot_id, core, applied, revision
        )
        return JSONResponse(
            jsonable_encoder(
                {
                    "contract_version": "bff.showcase.v1",
                    "meta": {
                        "world_id": world_id,
                        "lot_id": lot_id,
                        "freshness": revision["status"] if revision else "STALE",
                        "correlation_id": correlation_id_of(request),
                    },
                    "timeline": timeline,
                    "dispatch": dispatch,
                    "identities": {
                        "command_id": None if hold is None else str(hold["command_id"]),
                        "simulator_event_ref": None
                        if hold is None
                        else hold.get("causation_id"),
                        "event_id": None if outbox is None else outbox.get("event_id"),
                        "outbox_id": None
                        if outbox is None
                        else outbox.get("outbox_id"),
                        "twin_source_event_id": None
                        if revision is None
                        else revision.get("source_event_id"),
                        "twin_status": None
                        if revision is None
                        else revision.get("status"),
                    },
                    **observability,
                }
            ),
            headers={"Cache-Control": "no-store"},
        )

    return app


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "cap_demo_runtime.bff:create_app", host="0.0.0.0", port=8082, factory=True
    )
