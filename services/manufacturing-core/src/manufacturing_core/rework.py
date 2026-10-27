"""Internal append-only rework history values (WP-CORE-004, FR-CORE-009).

These values record execution facts supplied by Core; they do not execute a
directive, authorize a protected command, dispatch work, or change route state.
Approval/policy states and counts are provenance, not an authorization decision.
No numeric policy limits or public command contract are defined here.
"""

from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from manufacturing_core.domain import Entity, Identity, ManufacturingRoute, Revision


class ProcessExecutionRecord(Entity):
    """A separate historical visit, including a repeat of the same route step."""

    component_id: Identity
    lot_id: Identity
    route_visit_id: Identity
    equipment_id: Identity
    started_at: AwareDatetime
    ended_at: AwareDatetime

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if self.ended_at < self.started_at:
            raise ValueError("execution end precedes start")
        return self


class ExecutionSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    route: ManufacturingRoute
    executions: Annotated[tuple[ProcessExecutionRecord, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def valid_visits(self) -> Self:
        visits = {visit.id for visit in self.route.visits}
        if any(record.route_visit_id not in visits for record in self.executions):
            raise ValueError("execution references an unknown route visit")
        if len({record.id for record in self.executions}) != len(self.executions):
            raise ValueError("duplicate execution identity")
        return self


class ReworkDirective(Entity):
    """Component-scoped directive snapshot, not a protected-action payload.

    The origin execution identifies the prior step and its exact route snapshot.
    The return visit belongs to the original route. Revisions remain opaque.
    """

    component_id: Identity
    reason: Identity
    originating_inspection_id: Identity
    origin_execution_id: Identity
    return_visit_id: Identity
    rework_route_id: Identity
    rework_route_revision: Revision
    related_defect_id: Identity | None = None
    related_incident_id: Identity | None = None
    current_rework_count: Annotated[int, Field(strict=True, ge=0)]
    approval_state: Identity
    policy_state: Identity


class ReworkExecutionSegment(ExecutionSegment):
    directive: ReworkDirective

    @model_validator(mode="after")
    def matches_directive(self) -> Self:
        if (self.route.id, self.route.revision) != (
            self.directive.rework_route_id,
            self.directive.rework_route_revision,
        ):
            raise ValueError("rework route does not match directive revision")
        if any(
            record.component_id != self.directive.component_id
            for record in self.executions
        ):
            raise ValueError("rework execution targets a different component")
        return self


class ComponentExecutionHistory(BaseModel):
    """Immutable history in append order; timestamps retain occurrence time.

    No lifecycle, current route pointer or active lot membership is inferred.
    Lot references capture membership at execution time; identity never changes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    component_id: Identity
    original: ExecutionSegment
    rework: tuple[ReworkExecutionSegment, ...] = ()

    @model_validator(mode="after")
    def consistent_history(self) -> Self:
        executions: set[str] = set()
        directives: set[str] = set()
        return_visits = {visit.id for visit in self.original.route.visits}
        for segment in (self.original, *self.rework):
            if isinstance(segment, ReworkExecutionSegment):
                directive = segment.directive
                if directive.id in directives:
                    raise ValueError("duplicate rework directive identity")
                if directive.origin_execution_id not in executions:
                    raise ValueError("rework origin must reference prior execution")
                if directive.return_visit_id not in return_visits:
                    raise ValueError("rework return visit is not on original route")
                directives.add(directive.id)
            for record in segment.executions:
                if record.component_id != self.component_id:
                    raise ValueError("history targets a different component")
                if record.id in executions:
                    raise ValueError("duplicate execution identity across history")
                executions.add(record.id)
        return self

    def append_rework(
        self, segment: ReworkExecutionSegment
    ) -> "ComponentExecutionHistory":
        """Return validated extended history; preserve every existing snapshot.

        This is a pure value operation, not ExecuteApprovedReworkDirective.
        Persistence, concurrency, replay policy and lifecycle binding are later
        work; the caller must not treat this return value as execution authority.
        """
        return ComponentExecutionHistory(
            component_id=self.component_id,
            original=self.original,
            rework=(*self.rework, segment),
        )
