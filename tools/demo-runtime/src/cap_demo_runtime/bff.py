from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from operations_bff.composition import RuntimeSettings, build_app
from operations_bff.config import CookieSettings, LoginConfig, SessionConfig
from operations_bff.facility_state import (
    FacilityStateService,
    FacilityStateReader,
    FacilityStateSnapshot,
    LotState,
    RoutePosition,
    TWIN_SOURCE,
)
from operations_bff.overview import (
    AttentionFact,
    AttentionReader,
    OverviewQuery,
    OverviewService,
    SourceSnapshot,
)
from operations_bff.oidc import OidcSettings

from .config import Settings


def _connection(settings: Settings) -> psycopg.Connection[Any]:
    return psycopg.connect(settings.pg_dsn, row_factory=dict_row, connect_timeout=10)


class TwinReader(FacilityStateReader, AttentionReader):
    name = TWIN_SOURCE

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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
        allow_insecure_http=os.environ.get("OPERATIONS_BFF_OIDC_ALLOW_INSECURE_HTTP") == "1",
        browser_issuer=os.environ.get("OPERATIONS_BFF_OIDC_BROWSER_ISSUER") or None,
    )
    runtime = RuntimeSettings(
        oidc=oidc,
        cookie=CookieSettings(same_site="lax"),
        session=SessionConfig(),
        login=LoginConfig(),
        post_login_path="/",
    )
    reader = TwinReader(settings)
    return build_app(
        runtime,
        overview=OverviewService(OverviewReader(reader)),
        facility_state=FacilityStateService(reader),
    )


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run("cap_demo_runtime.bff:create_app", host="0.0.0.0", port=8082, factory=True)
