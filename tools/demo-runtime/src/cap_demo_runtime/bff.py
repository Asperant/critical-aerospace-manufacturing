from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen

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
        import json

        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise RuntimeError("Core showcase query returned a non-object")
    return value


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
