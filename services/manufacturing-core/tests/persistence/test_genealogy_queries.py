"""Focused genealogy reads over real PostgreSQL; synthetic stored facts only."""

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from statistics import median
from time import perf_counter

import psycopg
import pytest
from conftest import Database
from manufacturing_core.database import connect_runtime
from manufacturing_core.domain import (
    Equipment,
    Lot,
    ManufacturingRoute,
    RouteVisit,
    SerializedComponent,
)
from manufacturing_core.genealogy_queries import (
    CohortExposureRequest,
    ComponentTraceRequest,
    EquipmentExposureRequest,
    GenealogyQueries,
    LotTraceRequest,
)
from manufacturing_core.lineage import LotLineageHistory, LotMembershipSnapshot
from manufacturing_core.lineage_repository import LotLineageRepository
from manufacturing_core.repository import CoreRepository
from manufacturing_core.rework import (
    ComponentExecutionHistory,
    ExecutionSegment,
    ProcessExecutionRecord,
    ReworkDirective,
    ReworkExecutionSegment,
)
from manufacturing_core.rework_repository import ReworkHistoryRepository
from psycopg.rows import DictRow
from pydantic import ValidationError
from test_lineage_persistence import lineage_database as lineage_database
from test_lineage_persistence import seed as seed_lineage

pytestmark = pytest.mark.integration
BASE = datetime(2026, 10, 24, 10, tzinfo=UTC)


@pytest.fixture(scope="module")
def query_database(lineage_database: Database) -> Database:  # noqa: F811
    return lineage_database


@pytest.fixture
def query_connection(query_database: Database) -> Iterator[psycopg.Connection[DictRow]]:
    with (
        connect_runtime(query_database.runtime_dsn) as conn,
        conn.transaction(force_rollback=True),
    ):
        yield conn


def seed_execution(
    conn: psycopg.Connection[DictRow], component: str = "C1"
) -> ComponentExecutionHistory:
    repo = CoreRepository(conn)
    for equipment in ("EQ-A", "EQ-PLANNED"):
        if repo.get(Equipment, equipment) is None:
            repo.insert(Equipment(id=equipment, revision="r"))

    def segment(n: int) -> ExecutionSegment:
        route = ManufacturingRoute(
            id="R",
            revision=f"snapshot-{n}",
            visits=(
                RouteVisit(
                    id="VISIT",
                    revision="r",
                    route_id="R",
                    operation_class_id="CNC",
                    equipment_id="EQ-A",
                ),
                RouteVisit(
                    id="PLAN",
                    revision="r",
                    route_id="R",
                    operation_class_id="INSPECTION",
                    equipment_id="EQ-PLANNED",
                ),
            ),
        )
        record = ProcessExecutionRecord(
            id=f"{component}-EX-{n}",
            revision="opaque",
            component_id=component,
            lot_id="ROOT",
            route_visit_id="VISIT",
            equipment_id="EQ-A",
            started_at=BASE + timedelta(hours=n),
            ended_at=BASE + timedelta(hours=n, minutes=30),
        )
        return ExecutionSegment(route=route, executions=(record,))

    original, rework = segment(0), segment(1)
    result = ComponentExecutionHistory(
        component_id=component,
        original=original,
        rework=(
            ReworkExecutionSegment(
                **rework.model_dump(),
                directive=ReworkDirective(
                    id=f"{component}-DIR",
                    revision="r",
                    component_id=component,
                    reason="synthetic rework",
                    originating_inspection_id="I-1",
                    origin_execution_id=original.executions[0].id,
                    return_visit_id="VISIT",
                    rework_route_id="R",
                    rework_route_revision="snapshot-1",
                    current_rework_count=0,
                    approval_state="RECORDED",
                    policy_state="RECORDED",
                ),
            ),
        ),
    )
    ReworkHistoryRepository(conn).create(result)
    return result


def test_rework_retrieval_preserves_directive_route_and_visits(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    seed_lineage(query_connection)
    h = seed_execution(query_connection)
    queries = GenealogyQueries(query_connection)
    assert queries.rework_history("C1") == h
    assert (
        queries.rework_history("C2") is None
    )  # Known identity with no recorded history.
    assert queries.rework_history("MISSING") is None


@pytest.mark.parametrize(
    "lot,expected",
    [
        ("ROOT", []),
        ("A", ["E1"]),
        ("M", ["E1", "E2", "E3"]),
        ("FINAL", ["E1", "E2", "E3", "E4"]),
    ],
)
def test_split_merge_and_multigeneration(
    query_connection: psycopg.Connection[DictRow], lot: str, expected: list[str]
) -> None:
    h = seed_lineage(query_connection)
    # Persist reversed delivery order, then query causal temporal order.
    stored = LotLineageHistory(
        world_id=h.world_id, roots=h.roots, events=tuple(reversed(h.events))
    )
    LotLineageRepository(query_connection).create(stored)
    result = GenealogyQueries(query_connection).lot(
        LotTraceRequest(world_id=h.world_id, lot_id=lot)
    )
    assert result is not None
    assert [f.event.id for f in result.events] == expected
    for fact in result.events:
        assert fact.event == stored.events[fact.position]
    if lot == "M":
        assert result.events[-1].event.parent_lot_ids == ("B", "A1")
        assert result.events[-1].event.parent_child_links == (("B", "M"), ("A1", "M"))
    assert LotLineageRepository(query_connection).get(h.world_id) == stored


def test_forward_impact_and_component_memberships(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    h = seed_lineage(query_connection)
    LotLineageRepository(query_connection).create(h)
    queries = GenealogyQueries(query_connection)
    forward = queries.lot(
        LotTraceRequest(world_id=h.world_id, lot_id="A", direction="FORWARD")
    )
    assert forward is not None
    assert [f.event.id for f in forward.events] == ["E2", "E3", "E4"]
    component = queries.component(
        ComponentTraceRequest(world_id=h.world_id, component_id="C1")
    )
    assert component is not None
    assert component.focus_lot_ids == ("A", "A1", "FINAL", "M", "ROOT")
    assert [f.event.id for f in component.events] == ["E1", "E2", "E3", "E4"]
    assert "B" not in component.focus_lot_ids  # Merge context is not target membership.


@pytest.mark.parametrize("world,identity", [("MISSING", "FINAL"), ("KNOWN", "MISSING")])
def test_unknown_identity_is_explicit(
    query_connection: psycopg.Connection[DictRow], world: str, identity: str
) -> None:
    h = seed_lineage(query_connection)
    LotLineageRepository(query_connection).create(h)
    queries = GenealogyQueries(query_connection)
    actual_world = h.world_id if world == "KNOWN" else world
    assert queries.lot(LotTraceRequest(world_id=actual_world, lot_id=identity)) is None
    assert (
        queries.component(
            ComponentTraceRequest(world_id=actual_world, component_id=identity)
        )
        is None
    )


def test_deterministic_ties_and_recording_time(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    h = seed_lineage(query_connection)
    events = tuple(
        event.model_copy(
            update={
                "occurred_at": BASE,
                "effective_from": BASE,
                "recorded_at": BASE - timedelta(days=n),
            }
        )
        for n, event in enumerate(h.events)
    )
    stored = LotLineageHistory(
        world_id=h.world_id, roots=h.roots, events=tuple(reversed(events))
    )
    LotLineageRepository(query_connection).create(stored)
    queries = GenealogyQueries(query_connection)
    first = queries.lot(LotTraceRequest(world_id=h.world_id, lot_id="FINAL"))
    second = queries.lot(LotTraceRequest(world_id=h.world_id, lot_id="FINAL"))
    assert first == second
    assert first is not None
    assert [f.event.id for f in first.events] == ["E1", "E2", "E3", "E4"]
    assert [f.position for f in first.events] == [3, 2, 1, 0]


def exposure(
    equipment: str = "EQ-A",
    start: datetime = BASE,
    end: datetime = BASE + timedelta(hours=2),
    operation: str | None = None,
) -> EquipmentExposureRequest:
    return EquipmentExposureRequest(
        equipment_id=equipment,
        started_at=start,
        ended_at=end,
        operation_class_id=operation,
    )


def test_actual_exposure_returns_reentrant_visits_and_route_provenance(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    seed_lineage(query_connection)
    history = seed_execution(query_connection)
    queries = GenealogyQueries(query_connection)
    rows = queries.equipment_exposure(exposure())
    assert [r.execution for r in rows] == [
        history.original.executions[0],
        history.rework[0].executions[0],
    ]
    assert [r.route_revision for r in rows] == ["snapshot-0", "snapshot-1"]
    assert [r.directive_id for r in rows] == [None, "C1-DIR"]
    assert queries.equipment_exposure(exposure("EQ-PLANNED")) == ()
    assert queries.equipment_exposure(exposure("UNKNOWN")) == ()
    assert queries.equipment_exposure(exposure(operation="INSPECTION")) == ()
    assert queries.equipment_exposure(exposure(operation="CNC")) == rows


def test_half_open_window_and_temporal_order(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    seed_lineage(query_connection)
    seed_execution(query_connection)
    queries = GenealogyQueries(query_connection)
    assert (
        queries.equipment_exposure(
            exposure(start=BASE + timedelta(minutes=30), end=BASE + timedelta(hours=1))
        )
        == ()
    )
    rows = queries.equipment_exposure(
        exposure(
            start=BASE + timedelta(hours=1), end=BASE + timedelta(hours=1, minutes=1)
        )
    )
    assert [r.execution.id for r in rows] == ["C1-EX-1"]
    assert queries.equipment_exposure(exposure()) == queries.equipment_exposure(
        exposure()
    )


def test_common_equipment_counts_components_not_rework_visits(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    seed_lineage(query_connection)
    seed_execution(query_connection, "C1")
    seed_execution(query_connection, "C2")
    result = GenealogyQueries(query_connection).common_equipment_exposure(
        CohortExposureRequest(component_ids=("UNKNOWN", "C2", "C1"))
    )
    assert result.requested_component_ids == ("C1", "C2", "UNKNOWN")
    assert result.missing_history_ids == ("UNKNOWN",)
    assert len(result.exposures) == 1
    actual = result.exposures[0]
    assert (actual.equipment_id, actual.operation_class_id) == ("EQ-A", "CNC")
    assert actual.affected_count == 2
    assert actual.affected_ratio == 2 / 3
    assert actual.execution_ids == ("C1-EX-0", "C1-EX-1", "C2-EX-0", "C2-EX-1")


@pytest.mark.parametrize(
    "bad", ["time", "identity", "direction", "cohort", "duplicate"]
)
def test_invalid_requests_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        if bad == "time":
            exposure(start=BASE, end=BASE)
        elif bad == "identity":
            LotTraceRequest(world_id="W", lot_id=" ")
        elif bad == "direction":
            LotTraceRequest.model_validate(
                {"world_id": "W", "lot_id": "L", "direction": "ANY"}
            )
        else:
            CohortExposureRequest(component_ids=() if bad == "cohort" else ("C1", "C1"))


def test_correlated_logs(
    query_connection: psycopg.Connection[DictRow], caplog: pytest.LogCaptureFixture
) -> None:
    h = seed_lineage(query_connection)
    LotLineageRepository(query_connection).create(h)
    seed_execution(query_connection)
    with caplog.at_level(logging.INFO, logger="manufacturing_core"):
        GenealogyQueries(query_connection).lot(
            LotTraceRequest(world_id=h.world_id, lot_id="FINAL"),
            correlation_id="genealogy-test",
        )
    log = json.loads(caplog.records[-1].message)
    assert log["correlation_id"] == "genealogy-test"
    assert log["operation"] == "genealogy.lot"
    assert log["outcome"] == "SUCCESS"
    assert "ROOT" not in caplog.text


def test_read_health_and_unknown_history(query_database: Database) -> None:
    with connect_runtime(query_database.runtime_dsn) as conn, conn.transaction():
        conn.execute("SET TRANSACTION READ ONLY")
        queries = GenealogyQueries(conn)
        assert queries.health(correlation_id="read-health").status == "READY"
        assert (
            queries.lot(LotTraceRequest(world_id="unknown", lot_id="unknown")) is None
        )
        assert queries.rework_history("unknown") is None
        assert queries.equipment_exposure(exposure("unknown")) == ()
        assert queries.common_equipment_exposure(
            CohortExposureRequest(component_ids=("unknown",))
        ).missing_history_ids == ("unknown",)


def test_health_fails_closed_when_a_required_table_is_unavailable(
    database: Database,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with psycopg.connect(database.admin_dsn, autocommit=True) as admin:
        admin.execute("ALTER TABLE core.lineage_lot RENAME TO lineage_lot_unavailable")
        try:
            with (
                connect_runtime(database.runtime_dsn) as conn,
                conn.transaction(),
                caplog.at_level(logging.INFO, logger="manufacturing_core"),
            ):
                conn.execute("SET TRANSACTION READ ONLY")
                queries = GenealogyQueries(conn)
                assert queries.health(correlation_id="missing-schema").status == (
                    "UNAVAILABLE"
                )
                with pytest.raises(psycopg.errors.UndefinedTable):
                    queries.lot(
                        LotTraceRequest(world_id="W", lot_id="L"),
                        correlation_id="failed-query",
                    )
                assert json.loads(caplog.records[-1].message)["outcome"] == "FAILED"
        finally:
            admin.execute(
                "ALTER TABLE core.lineage_lot_unavailable RENAME TO lineage_lot"
            )


def test_independent_time_ties_and_world_isolation(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    h = seed_lineage(query_connection)
    repo = CoreRepository(query_connection)
    for name in ("B1", "B2"):
        repo.insert(Lot(id=name, revision="r", order_id="O"))
    repo.insert(SerializedComponent(id="C4", revision="r", lot_id="ROOT"))

    def material(lot: str, *ids: str) -> LotMembershipSnapshot:
        return LotMembershipSnapshot(world_id=h.world_id, lot_id=lot, component_ids=ids)

    first = type(h.events[0]).model_validate(
        {
            **h.events[0].model_dump(),
            "children": (material("A", "C2", "C1"), material("B", "C3", "C4")),
        }
    )
    left = h.events[1]
    right = type(left).model_validate(
        {
            **left.model_dump(),
            "id": "E0",
            "source_event_id": "S0",
            "parent_lot_ids": ("B",),
            "children": (material("B1", "C3"), material("B2", "C4")),
        }
    )
    stored = LotLineageHistory(
        world_id=h.world_id,
        roots=(material("ROOT", "C1", "C2", "C3", "C4"),),
        events=(left, right, first),
    )
    LotLineageRepository(query_connection).create(stored)
    queries = GenealogyQueries(query_connection)
    result = queries.lot(
        LotTraceRequest(world_id=h.world_id, lot_id="ROOT", direction="FORWARD")
    )
    assert result is not None
    assert [f.event.id for f in result.events] == ["E1", "E0", "E2"]
    assert [f.position for f in result.events] == [2, 1, 0]
    assert queries.lot(LotTraceRequest(world_id="other-world", lot_id="ROOT")) is None


def test_wp_normal_query_sanity(query_connection: psycopg.Connection[DictRow]) -> None:
    """Bounded local measurement, never a final integrated performance claim."""
    h = seed_lineage(query_connection)
    seed_execution(query_connection)
    repo = CoreRepository(query_connection)
    # 999 independent terminal lots plus the diamond's FINAL = 1,000 terminal
    # lots; the six ancestors remain historical. 100 actual equipment identities.
    for n in range(98):
        repo.insert(Equipment(id=f"TOOL-{n}", revision="r"))
    roots = list(h.roots)
    equipment_ids = ("EQ-A", "EQ-PLANNED", *(f"TOOL-{n}" for n in range(98)))
    for n in range(999):
        lot_id, component_id = f"SCALE-L-{n}", f"SCALE-C-{n}"
        repo.insert(Lot(id=lot_id, revision="r", order_id="O"))
        repo.insert(SerializedComponent(id=component_id, revision="r", lot_id=lot_id))
        roots.append(
            LotMembershipSnapshot(
                world_id=h.world_id, lot_id=lot_id, component_ids=(component_id,)
            )
        )
        equipment = equipment_ids[n % 100]
        route = ManufacturingRoute(
            id="R",
            revision="scale-r",
            visits=(
                RouteVisit(
                    id="SCALE",
                    revision="r",
                    route_id="R",
                    operation_class_id="CNC",
                    equipment_id=equipment,
                ),
            ),
        )
        record = ProcessExecutionRecord(
            id=f"SCALE-X-{n}",
            revision="r",
            component_id=component_id,
            lot_id=lot_id,
            route_visit_id="SCALE",
            equipment_id=equipment,
            started_at=BASE,
            ended_at=BASE + timedelta(minutes=1),
        )
        ReworkHistoryRepository(query_connection).create(
            ComponentExecutionHistory(
                component_id=component_id,
                original=ExecutionSegment(route=route, executions=(record,)),
            )
        )
    LotLineageRepository(query_connection).create(
        LotLineageHistory(world_id=h.world_id, roots=tuple(roots), events=h.events)
    )
    queries = GenealogyQueries(query_connection)
    samples: dict[str, list[float]] = {"ancestry": [], "exposure": []}
    for _ in range(30):
        started = perf_counter()
        ancestry = queries.lot(LotTraceRequest(world_id=h.world_id, lot_id="FINAL"))
        samples["ancestry"].append((perf_counter() - started) * 1000)
        assert ancestry is not None and len(ancestry.events) == 4
        started = perf_counter()
        actual = queries.equipment_exposure(exposure("TOOL-0"))
        samples["exposure"].append((perf_counter() - started) * 1000)
        assert len(actual) == 10
    print(
        "WP_NORMAL_QUERY_SANITY",
        json.dumps(
            {
                name: {
                    "samples": len(values),
                    "median_ms": round(median(values), 3),
                    "p95_ms": round(sorted(values)[28], 3),
                    "max_ms": round(max(values), 3),
                }
                for name, values in samples.items()
            },
            sort_keys=True,
        ),
    )


def test_zero_duration_visit_respects_window_boundaries(
    query_connection: psycopg.Connection[DictRow],
) -> None:
    seed_lineage(query_connection)
    history = seed_execution(query_connection)
    instant = history.original.executions[0].model_copy(
        update={"id": "C2-INSTANT", "component_id": "C2", "ended_at": BASE}
    )
    ReworkHistoryRepository(query_connection).create(
        ComponentExecutionHistory(
            component_id="C2",
            original=ExecutionSegment(
                route=history.original.route, executions=(instant,)
            ),
        )
    )
    queries = GenealogyQueries(query_connection)
    included = queries.equipment_exposure(
        exposure(start=BASE, end=BASE + timedelta(seconds=1))
    )
    assert "C2-INSTANT" in {row.execution.id for row in included}
    excluded = queries.equipment_exposure(
        exposure(start=BASE - timedelta(seconds=1), end=BASE)
    )
    assert excluded == ()
