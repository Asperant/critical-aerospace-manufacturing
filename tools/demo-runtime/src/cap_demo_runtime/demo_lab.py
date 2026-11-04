"""Presenter-facing Demo Lab adapters over the real project components.

The module is deliberately a thin demo boundary.  It does not invent state or
replace Core authority: Vision, Simulator and Scheduler are called as libraries,
while the quality excursion sends the same commands to the internal Core HTTP
boundary used by the existing showcase.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from fractions import Fraction
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import NAMESPACE_URL, uuid5

import nats
import psycopg
from cap_artifacts import ArtifactStore, S3Client, StoreConfig
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from manufacturing_scheduler import (
    OfflineInstanceConfig,
    generate,
    get_baseline,
    get_policy,
)
from manufacturing_simulator import Kernel, ListPublisher, ScenarioEngine, fifo
from manufacturing_simulator.operations import (
    KINDS,
    EquipmentSpec,
    FacilityConfig,
    LotSpec,
    OperationalFacility,
    RouteSpec,
    VisitSpec,
    scenario_config,
)
from manufacturing_simulator.serialization import (
    event_sequence_digest,
    final_state_digest,
)
from operations_bff.api import Session, correlation_id_of
from psycopg.rows import DictRow, dict_row
from vision_service.baseline import ThresholdPolicy
from vision_service.image import SUPPORTED_CONTENT_TYPES
from vision_service.pipeline import inspect as inspect_image
from vision_service.request import parse_request

from .config import Settings

router = APIRouter(prefix="/v1/demo-lab")

WORLD_ID = "DEMO-WORLD"
BRANCH_ID = "PRIMARY"
CONSUMER_SCOPE = "twin-primary"
DEFAULT_LOT_ID = "DEMO-LOT-001"


def _connection(settings: Settings) -> psycopg.Connection[DictRow]:
    return psycopg.Connection[DictRow].connect(
        settings.pg_dsn, row_factory=dict_row, connect_timeout=10
    )


def _bounded_int(value: Any, name: str, *, minimum: int, maximum: int, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise HTTPException(422, detail=f"{name} must be an integer in {minimum}..{maximum}")
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if hasattr(value, "value"):
        return value.value
    return value


def _simulation_state(world_id: str, facility: OperationalFacility, now: int) -> dict[str, Any]:
    return {
        "world_id": world_id,
        "state_revision": facility.state_revision,
        "simulation_time": now,
        "lots": [
            {
                "lot_id": report.lot_id,
                "revision": report.revision,
                "lifecycle": report.lifecycle,
                "execution_state": report.execution_state,
                "held": report.held,
                "current_visit": report.current_visit,
                "rework_count": report.rework_count,
                "execution_count": len(report.executions),
            }
            for report in facility.lot_reports()
        ],
        "machines": [
            {
                "machine_id": report.equipment_id,
                "state": report.state,
                "health": report.health,
                "usage": report.usage,
                "lot_id": report.lot_id,
            }
            for report in facility.equipment_reports()
        ],
        "provenance": "SIMULATOR_OPERATIONAL_STATE",
    }


def _simulation_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build presenter lanes from the simulator's allow-listed operational facts."""
    timeline: list[dict[str, Any]] = []
    for sequence, event in enumerate(events, start=1):
        attributes = event.get("attributes") or {}
        machine_id = attributes.get("machine_id")
        timeline.append(
            {
                "sequence": sequence,
                "time": event["time"],
                "kind": event["kind"],
                "lane": "MAKİNE" if machine_id else "LOT",
                "lot_id": attributes.get("lot_id"),
                "machine_id": machine_id,
                "route_step": attributes.get("route_step"),
                "attributes": attributes,
            }
        )
    return timeline


def _simulation_gantt(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair published start/completion facts into presenter-safe Gantt bars.

    The simulator intentionally exposes no predicted end time.  An operation
    without a published completion therefore remains open-ended in the result.
    Equipment failure facts are attached only when their timestamp falls inside
    the corresponding published operation interval.
    """
    active: dict[tuple[str, str, str], dict[str, Any]] = {}
    completed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for sequence, event in enumerate(events, start=1):
        attributes = event.get("attributes") or {}
        lot_id = attributes.get("lot_id")
        machine_id = attributes.get("machine_id")
        route_step = attributes.get("route_step")
        kind = event.get("kind")
        if kind == "EQUIPMENT_FAILED" and machine_id:
            failures.append({"sequence": sequence, "time": event["time"], "machine_id": machine_id})
        if not (isinstance(lot_id, str) and isinstance(machine_id, str) and isinstance(route_step, str)):
            continue
        key = (lot_id, machine_id, route_step)
        if kind == "DISPATCH_STARTED":
            active[key] = {
                "lot_id": lot_id,
                "machine_id": machine_id,
                "route_step": route_step,
                "start_time": event["time"],
                "start_sequence": sequence,
            }
        elif kind == "PROCESS_COMPLETED":
            bar = active.pop(key, None)
            if bar is not None:
                bar["end_time"] = event["time"]
                bar["end_sequence"] = sequence
                completed.append(bar)
    bars = completed + list(active.values())
    for bar in bars:
        end_time = bar.get("end_time")
        bar["status"] = "COMPLETED" if end_time is not None else "IN_PROGRESS"
        bar["failure_events"] = [
            failure
            for failure in failures
            if failure["machine_id"] == bar["machine_id"]
            and failure["time"] >= bar["start_time"]
            and (end_time is None or failure["time"] <= end_time)
        ]
    return sorted(bars, key=lambda item: (item["start_time"], item["machine_id"], item["lot_id"]))


def _core_json(settings: Settings, path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = UrlRequest(
        f"{settings.core_url.rstrip('/')}{path}",
        method=method,
        data=payload,
        headers={"Content-Type": "application/json"} if payload else {},
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - configured internal demo boundary
            value = json.loads(response.read())
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read()).get("detail", "Core request failed")
        except (ValueError, AttributeError):
            detail = "Core request failed"
        raise HTTPException(exc.code, detail=detail) from None
    except (URLError, TimeoutError) as exc:
        raise HTTPException(503, detail=f"Core unavailable: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise HTTPException(502, detail="Core returned an invalid response")
    return value


def _simulator_run(
    *,
    world_id: str,
    seed: int,
    horizon: int,
    max_events: int,
    lot_count: int,
    defect_per_mille: int,
    failure_at: int | None,
) -> dict[str, Any]:
    equipment = tuple(
        EquipmentSpec(f"DEMO-CNC-{index:02d}", ("ROUGH-MACHINING",))
        for index in range(1, 3)
    )
    lots = tuple(
        LotSpec(
            f"SIM-LOT-{index:03d}",
            "SIM-ORDER-001",
            "SIM-ROUTE",
            release_at=index - 1,
            priority=(index % 3) + 1,
            due_at=max(10, index * 8),
        )
        for index in range(1, lot_count + 1)
    )
    failures = ()
    if failure_at is not None:
        from manufacturing_simulator.operations import FailureSpec

        failures = (FailureSpec("DEMO-CNC-01", failure_at),)
    config = FacilityConfig(
        world_id=world_id,
        equipment=equipment,
        routes=(
            RouteSpec(
                "SIM-ROUTE",
                "sim-route-rev-1",
                (
                    VisitSpec(
                        "SIM-VISIT-1",
                        "ROUGH-MACHINING",
                        tuple(item.equipment_id for item in equipment),
                        2,
                        inspect=True,
                        defect_per_mille=defect_per_mille,
                    ),
                ),
            ),
        ),
        lots=lots,
        failures=failures,
    )
    publisher = ListPublisher()
    facility = OperationalFacility(config, provider=fifo(), publisher=publisher)
    scenario = scenario_config(
        config,
        seed=seed,
        horizon=horizon,
        scenario_id="demo-lab-simulation",
    )
    world = ScenarioEngine(KINDS).initialize(scenario)
    kernel = Kernel(world, facility.handlers())
    initial_state = _simulation_state(world_id, facility, 0)
    result = kernel.run(until=horizon, max_events=max_events)
    final_state = _simulation_state(world_id, facility, result.now)
    records = [
        {
            "sequence": record.sequence,
            "time": record.time,
            "kind": record.kind,
            "event_id": record.event_id,
            "payload": _json_value(record.payload),
            "outcome": _json_value(record.outcome),
        }
        for record in kernel.records()
    ]
    operational_events = [event.to_document() for event in publisher.events]
    return {
        "provenance": "SIMULATION",
        "scenario": {
            "id": scenario.scenario_id,
            "version": scenario.scenario_version,
            "seed": seed,
            "horizon": horizon,
            "max_events": max_events,
            "lot_count": lot_count,
            "defect_per_mille": defect_per_mille,
            "failure_at": failure_at,
            "config_digest": config.digest(),
        },
        "result": {
            "termination": result.termination.value,
            "processed_events": result.processed,
            "simulation_time": result.now,
            "queue_depth": result.queue_depth,
            "event_sequence_digest": event_sequence_digest(kernel.records()),
            "final_state_digest": final_state_digest(world),
        },
        "state": {
            "initial": initial_state,
            "final": final_state,
        },
        "records": records,
        "operational_events": operational_events,
        "timeline": _simulation_timeline(operational_events),
        "gantt": _simulation_gantt(operational_events),
    }


def _vision_store() -> tuple[ArtifactStore, S3Client]:
    try:
        client = S3Client(StoreConfig.from_env(role="writer"))
    except Exception as exc:
        raise HTTPException(503, detail=f"Vision artifact store unavailable: {type(exc).__name__}") from exc
    return ArtifactStore(client), client


def _nats_info(settings: Settings) -> dict[str, Any]:
    async def read() -> dict[str, Any]:
        connection = await nats.connect(settings.nats_url, connect_timeout=5)
        try:
            js = connection.jetstream()
            stream = await js.stream_info(settings.stream)
            consumer = await js.consumer_info(settings.stream, settings.consumer_scope)
            return {
                "stream": stream.config.name,
                "subjects": list(stream.config.subjects or []),
                "messages": stream.state.messages,
                "consumer": consumer.name,
                "num_ack_pending": consumer.num_ack_pending,
                "num_redelivered": consumer.num_redelivered,
            }
        finally:
            await connection.close()

    try:
        return asyncio.run(asyncio.wait_for(read(), timeout=5))
    except Exception as exc:
        return {"status": "UNAVAILABLE", "detail": type(exc).__name__}


def _lot_state(settings: Settings, lot_id: str) -> dict[str, Any] | None:
    try:
        value = _core_json(settings, f"/v1/lots/{quote(lot_id, safe='')}")
    except HTTPException as exc:
        if exc.status_code == 404:
            return None
        raise
    return {
        "id": value.get("id", lot_id),
        "revision": value.get("revision"),
        "lifecycle_state": value.get("lifecycle_state"),
        "execution_state": value.get("execution_state"),
        "held": value.get("held"),
    }


def _wait_for_projection(settings: Settings, lot_id: str, event_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        showcase = _core_json(
            settings,
            f"/v1/showcase/{quote(lot_id, safe='')}?world_id={quote(settings.world_id, safe='')}",
        )
        outbox_value = showcase.get("outbox")
        with _connection(settings) as connection:
            applied = connection.execute(
                "SELECT consumer_scope, event_id, world_id, branch_id, aggregate_type, "
                "aggregate_id, aggregate_version FROM twin.applied_event "
                "WHERE event_id=%s AND consumer_scope=%s",
                (event_id, settings.consumer_scope),
            ).fetchone()
            projection = connection.execute(
                "SELECT aggregate_id, world_id, branch_id, aggregate_version, state, "
                "source_event_id, source_revision FROM twin.projection_entity "
                "WHERE aggregate_id=%s AND world_id=%s AND branch_id=%s",
                (lot_id, settings.world_id, settings.branch_id),
            ).fetchone()
            revision = connection.execute(
                "SELECT source_event_id, status FROM twin.projection_revision "
                "WHERE world_id=%s AND branch_id=%s",
                (settings.world_id, settings.branch_id),
            ).fetchone()
        if outbox_value and outbox_value.get("event_id") == event_id and outbox_value.get("publication_status") == "PUBLISHED" and applied and projection:
            return {
                "outbox": dict(outbox_value),
                "twin_applied_event": dict(applied),
                "twin_projection": dict(projection),
                "twin_revision": None if revision is None else dict(revision),
            }
        time.sleep(0.25)
    raise HTTPException(504, detail="Event did not reach the Twin projection in time")


def _quality_simulator(world_id: str, lot_id: str, seed: int) -> dict[str, Any]:
    config = FacilityConfig(
        world_id=world_id,
        equipment=(EquipmentSpec("DEMO-CNC-01", ("ROUGH-MACHINING",)),),
        routes=(
            RouteSpec(
                "DEMO-ROUTE",
                "route-rev-1",
                (VisitSpec("DEMO-VISIT-1", "ROUGH-MACHINING", ("DEMO-CNC-01",), 1, inspect=True, defect_per_mille=1000),),
            ),
        ),
        lots=(LotSpec(lot_id, "DEMO-ORDER-001", "DEMO-ROUTE", release_at=0),),
    )
    publisher = ListPublisher()
    facility = OperationalFacility(config, provider=fifo(), publisher=publisher)
    scenario = scenario_config(config, seed=seed, horizon=100, scenario_id="demo-lab-quality-excursion")
    world = ScenarioEngine(KINDS).initialize(scenario)
    kernel = Kernel(world, facility.handlers())
    result = kernel.run_to_horizon(10_000)
    event = next((item for item in publisher.events if item.kind == "INSPECTION_FAILED"), None)
    if event is None:
        raise HTTPException(500, detail="Simulator did not produce INSPECTION_FAILED")
    return {
        "seed": seed,
        "scenario_id": scenario.scenario_id,
        "event_ref": f"{scenario.scenario_id}:{event.kind}:{event.time}",
        "event_type": event.kind,
        "event_time": event.time,
        "correlation_id": event.correlation_id,
        "processed_events": result.processed,
        "event_sequence_digest": event_sequence_digest(kernel.records()),
        "final_state_digest": final_state_digest(world),
        "provenance": event.provenance,
    }


@router.get("/capabilities", operation_id="getDemoLabCapabilities")
def capabilities(request: Request, auth: Session) -> dict[str, Any]:
    del auth
    settings: Settings = request.app.state.demo_lab_settings
    s3_ready = all(
        bool(os.environ.get(name, "").strip())
        for name in ("CAP_S3_ENDPOINT", "CAP_S3_ACCESS_KEY", "CAP_S3_SECRET_KEY")
    )
    return {
        "contract_version": "bff.demo-lab.capabilities.v1",
        "world_id": settings.world_id,
        "experiments": {
            "vision": {"available": s3_ready, "mode": "REAL_PIPELINE"},
            "simulation": {"available": True, "mode": "DETERMINISTIC_SIMULATION"},
            "quality_excursion": {"available": True, "mode": "REAL_CORE_EVENT_CHAIN"},
            "scheduling": {"available": True, "mode": "OFFLINE_BASELINES"},
            "event_trace": {"available": True, "mode": "POSTGRESQL_NATS_TWIN_READS"},
        },
        "ai": {"available": False, "reason": "AI runtime/orchestrator is not implemented"},
    }


@router.post("/vision/inspect", operation_id="runDemoLabVision")
async def vision_inspect(
    request: Request,
    auth: Session,
    world_id: str = Query(WORLD_ID, min_length=1, max_length=128, pattern=r"^\S+$"),
    lot_id: str = Query(DEFAULT_LOT_ID, min_length=1, max_length=128, pattern=r"^\S+$"),
    z_threshold: float = Query(6.5, ge=1.0, le=30.0),
    min_area_px: int = Query(24, ge=1, le=10000),
    max_candidates: int = Query(64, ge=1, le=256),
) -> dict[str, Any]:
    del auth
    settings: Settings = request.app.state.demo_lab_settings
    if world_id != settings.world_id:
        raise HTTPException(409, detail="world scope rejected")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(415, detail="Demo Lab Vision accepts PNG, JPG or JPEG")
    data = await request.body()
    if not data or len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, detail="Image must be between 1 byte and 12 MiB")
    store, client = _vision_store()
    try:
        simulation_run_id = f"demo-lab-vision-{uuid.uuid4()}"
        reference = store.store(
            data,
            artifact_type="inspection_image",
            artifact_class="OPERATIONAL_EVIDENCE",
            retention_class="RC-D",
            content_type=content_type,
            format_version=("png/1" if content_type == "image/png" else "jpeg/1"),
            logical_owner="demo-lab",
            producer={"service": "demo-bff", "version": "0.1.0"},
            classification="INTERNAL",
            context={"world_id": world_id, "simulation_run_id": simulation_run_id, "branch_id": settings.branch_id},
        )
        work = parse_request(
            {
                "inspection_request_id": str(uuid.uuid4()),
                "inspection_run_id": simulation_run_id,
                "world_id": world_id,
                "subject": {
                    "lot_id": lot_id,
                    "lot_revision": "demo-lab",
                    "serialized_component_id": f"{lot_id}-COMP-001",
                    "serialized_component_revision": "demo-lab",
                    "route_visit_id": "DEMO-VISIT-1",
                },
                "artifact": reference.to_dict(),
            }
        )
        observation = inspect_image(
            work,
            store,
            observation_id=str(uuid.uuid4()),
            clock=lambda: datetime.now(UTC),
            policy=ThresholdPolicy(
                version=f"demo-lab-local-contrast-z{z_threshold:g}-a{min_area_px}/2",
                z_threshold=z_threshold,
                min_area_px=min_area_px,
                max_candidates=max_candidates,
            ),
        )
        return {"contract_version": "bff.demo-lab.vision.v1", "observation": observation}
    finally:
        client.close()


@router.post("/simulation/runs", operation_id="runDemoLabSimulation")
def simulation_run(request: Request, auth: Session, body: dict[str, Any]) -> dict[str, Any]:
    del auth
    seed = _bounded_int(body.get("seed"), "seed", minimum=0, maximum=2**31 - 1, default=4242)
    horizon = _bounded_int(body.get("horizon"), "horizon", minimum=1, maximum=100_000, default=100)
    max_events = _bounded_int(body.get("max_events"), "max_events", minimum=1, maximum=50_000, default=10_000)
    lot_count = _bounded_int(body.get("lot_count"), "lot_count", minimum=1, maximum=20, default=4)
    defect = _bounded_int(body.get("defect_per_mille"), "defect_per_mille", minimum=0, maximum=1000, default=250)
    failure_at = body.get("failure_at")
    if failure_at is not None:
        failure_at = _bounded_int(failure_at, "failure_at", minimum=1, maximum=horizon, default=10)
    return {"contract_version": "bff.demo-lab.simulation.v1", "run": _simulator_run(world_id=WORLD_ID, seed=seed, horizon=horizon, max_events=max_events, lot_count=lot_count, defect_per_mille=defect, failure_at=failure_at)}


@router.post("/scheduling/compare", operation_id="compareDemoLabScheduling")
def scheduling_compare(request: Request, auth: Session, body: dict[str, Any]) -> dict[str, Any]:
    del request, auth
    seed = _bounded_int(body.get("seed"), "seed", minimum=0, maximum=2**63 - 1, default=4242)
    job_count = _bounded_int(body.get("job_count"), "job_count", minimum=1, maximum=100, default=12)
    now = _bounded_int(body.get("decision_tick"), "decision_tick", minimum=0, maximum=100_000, default=20)
    horizon = _bounded_int(body.get("horizon_ticks"), "horizon_ticks", minimum=0, maximum=100_000, default=100)
    config = OfflineInstanceConfig(job_count=job_count, horizon_ticks=horizon)
    instance = generate(config, seed)
    context = instance.context_at(now)
    results = []
    for policy_id in ("SCH-B1", "SCH-B2", "SCH-B3", "SCH-B4", "SCH-B5"):
        decision = get_policy(policy_id).select(context)
        definition = get_baseline(policy_id)
        job_by_id = {job.job_id: job for job in context.candidates}

        def key_display(value: Any) -> str:
            if isinstance(value, Fraction):
                return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
            return str(value)

        selected = job_by_id.get(decision.selected_job_id or "")
        selected_value = decision.ranking[0].key[0] if decision.ranking else None
        results.append(
            {
                "baseline_id": decision.policy_id,
                "name": decision.policy_name,
                "version": decision.policy_version,
                "status": decision.status.value,
                "decision_tick": decision.decision_tick,
                "selected_job_id": decision.selected_job_id,
                "rule_description": definition.method_description,
                "selection_reason": (
                    f"{decision.policy_name}, {decision.selected_job_id}: "
                    f"{key_display(selected_value)} öncelik anahtarı ile ilk sırada"
                    if selected is not None
                    else "Uygun aday yok"
                ),
                "selected_job": None if selected is None else asdict(selected) | {"state": selected.state.value},
                "ranking": [
                    {
                        "rank": rank,
                        "job_id": item.job_id,
                        "key": _json_value(item.key),
                        "priority_value": _json_value(item.key[0]),
                        "priority_display": key_display(item.key[0]),
                    }
                    for rank, item in enumerate(decision.ranking, start=1)
                ],
            }
        )
    return {
        "contract_version": "bff.demo-lab.scheduling.v1",
        "provenance": "SYNTHETIC_OFFLINE_FIXTURE: not real factory data",
        "instance": {
            "instance_id": instance.instance_id,
            "seed": seed,
            "generator_version": instance.metadata.generator_version,
            "config_sha256": instance.metadata.config_sha256,
            "decision_tick": now,
            "jobs": [asdict(job) | {"state": job.state.value, "dispatchable": job.is_dispatchable(now)} for job in instance.jobs],
        },
        "results": results,
    }


@router.post("/quality-excursion", operation_id="runDemoLabQualityExcursion")
def quality_excursion(
    request: Request,
    auth: Session,
    seed: int = Query(4242, ge=0, le=2**31 - 1),
    lot_id: str | None = Query(None, min_length=1, max_length=128, pattern=r"^\S+$"),
) -> dict[str, Any]:
    del auth
    settings: Settings = request.app.state.demo_lab_settings
    if lot_id is None:
        lot_id = f"DEMO-LAB-{uuid.uuid4().hex[:12].upper()}"
        _core_json(settings, "/v1/demo/lots", method="POST", body={"lot_id": lot_id})
    before = _lot_state(settings, lot_id)
    if before is None:
        raise HTTPException(404, detail="demo lot not found; use the seeded demo world")
    if before["held"]:
        raise HTTPException(409, detail="clean demo environment required: lot already has ACTIVE_HOLD; use the controlled demo reset")
    simulator = _quality_simulator(settings.world_id, lot_id, seed)
    correlation_id = f"demo-lab-quality-{uuid.uuid4()}"
    command_id = str(uuid5(NAMESPACE_URL, f"cap-demo/demo-lab/{lot_id}/{correlation_id}/hold"))
    hold_id = str(uuid5(NAMESPACE_URL, f"cap-demo/demo-lab/{lot_id}/{correlation_id}/hold-id"))
    hold = _core_json(
        settings,
        "/v1/commands",
        method="POST",
        body={
            "command_type": "PlaceLotOnHold",
            "command_version": 1,
            "command_id": command_id,
            "idempotency_key": correlation_id,
            "world_id": settings.world_id,
            "correlation_id": correlation_id,
            "causation_id": simulator["event_ref"],
            "target": {"entity_type": "Lot", "entity_id": lot_id},
            "expected": {"expected_revision": before["revision"]},
            "hold_reason": "Demo Lab simulator inspection anomaly",
            "material_hold_id": hold_id,
        },
    )
    reached = _wait_for_projection(settings, lot_id, str(hold["event_id"]))
    after = _lot_state(settings, lot_id)
    dispatch = _core_json(
        settings,
        "/v1/commands",
        method="POST",
        body={
            "command_type": "DispatchLot",
            "command_version": 1,
            "command_id": str(uuid5(NAMESPACE_URL, f"cap-demo/demo-lab/{lot_id}/{correlation_id}/dispatch")),
            "idempotency_key": f"{correlation_id}/dispatch",
            "world_id": settings.world_id,
            "correlation_id": f"{correlation_id}/dispatch",
            "target": {"entity_type": "Lot", "entity_id": lot_id},
            "expected": {"expected_revision": after["revision"] if after else before["revision"]},
            "operation_id": "DEMO-VISIT-1",
            "resource_id": "DEMO-CNC-01",
        },
    )
    return jsonable_encoder(
        {
            "contract_version": "bff.demo-lab.quality.v1",
            "world_id": settings.world_id,
            "lot_id": lot_id,
            "simulator": simulator,
            "core": {"before": before, "hold": hold, "after": after, "dispatch": dispatch},
            "transport": {"outbox": reached["outbox"], "nats": _nats_info(settings)},
            "twin": reached,
            "correlation_id": correlation_id_of(request),
        }
    )


@router.get("/event-trace", operation_id="getDemoLabEventTrace")
def event_trace(
    request: Request,
    auth: Session,
    world_id: str = Query(WORLD_ID, min_length=1, max_length=128, pattern=r"^\S+$"),
    lot_id: str = Query(DEFAULT_LOT_ID, min_length=1, max_length=128, pattern=r"^\S+$"),
) -> dict[str, Any]:
    del auth
    settings: Settings = request.app.state.demo_lab_settings
    if world_id != settings.world_id:
        raise HTTPException(409, detail="world scope rejected")
    state = _lot_state(settings, lot_id)
    core = _core_json(settings, f"/v1/showcase/{quote(lot_id, safe='')}?world_id={quote(world_id, safe='')}")
    with _connection(settings) as connection:
        latest = connection.execute(
            "SELECT event_id, applied_at FROM twin.applied_event WHERE consumer_scope=%s "
            "AND aggregate_id=%s AND world_id=%s ORDER BY applied_at DESC LIMIT 1",
            (settings.consumer_scope, lot_id, world_id),
        ).fetchone()
        revision = connection.execute(
            "SELECT source_event_id, status, updated_at FROM twin.projection_revision "
            "WHERE world_id=%s AND branch_id=%s",
            (world_id, settings.branch_id),
        ).fetchone()
    timeline: list[dict[str, str]] = []
    hold = core.get("hold_command")
    outbox = core.get("outbox")
    dispatch = core.get("dispatch_attempt")
    if hold:
        timeline.append(
            {
                "kind": "CORE_HOLD",
                "label": "Core hold",
                "status": str(hold.get("status", "UNKNOWN")),
                "source": "PostgreSQL core.command_outcome",
                "identity": str(hold.get("command_id") or hold.get("outcome_id") or ""),
            }
        )
    if outbox:
        timeline.append(
            {
                "kind": "OUTBOX",
                "label": "Core outbox",
                "status": str(outbox.get("publication_status", "UNKNOWN")),
                "source": "PostgreSQL core.outbox",
                "identity": str(outbox.get("event_id") or outbox.get("outbox_id") or ""),
            }
        )
    if latest is not None:
        timeline.append(
            {
                "kind": "TWIN_APPLIED",
                "label": "Digital Twin",
                "status": "APPLIED",
                "source": "PostgreSQL twin.applied_event",
                "identity": str(latest["event_id"]),
            }
        )
    if dispatch:
        timeline.append(
            {
                "kind": "DISPATCH",
                "label": "Dispatch attempt",
                "status": str(dispatch.get("status", "UNKNOWN")),
                "source": "PostgreSQL core.command_outcome",
                "identity": str(dispatch.get("command_id") or dispatch.get("outcome_id") or ""),
            }
        )
    core["timeline"] = timeline
    return jsonable_encoder(
        {
            "contract_version": "bff.demo-lab.trace.v1",
            "meta": {"world_id": world_id, "lot_id": lot_id, "correlation_id": correlation_id_of(request)},
            "core_state": state,
            "core_showcase": core,
            "twin": {"latest_applied_event": None if latest is None else dict(latest), "revision": None if revision is None else dict(revision)},
            "nats": _nats_info(settings),
            "identities": {
                "hold_command_id": None if hold is None else hold.get("command_id"),
                "hold_outcome_id": None if hold is None else hold.get("outcome_id"),
                "core_event_id": None if outbox is None else outbox.get("event_id"),
                "outbox_id": None if outbox is None else outbox.get("outbox_id"),
                "twin_applied_event_id": None if latest is None else latest.get("event_id"),
                "dispatch_command_id": None if dispatch is None else dispatch.get("command_id"),
            },
        }
    )


def mount_demo_lab(app: Any, settings: Settings) -> None:
    """Mount the router with settings held by the demo runtime composition root."""
    app.state.demo_lab_settings = settings
    app.include_router(router)
