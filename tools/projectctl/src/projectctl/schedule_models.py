from pydantic import BaseModel, ConfigDict

from .provenance import SourceRef


class Cycle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    title: str
    goal: str | None
    effective_week_end: int
    work_package_ids: list[str]
    provenance: SourceRef


class Milestone(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    title: str
    target_cycle: str
    effective_week_end: int
    raw_planning_status: str | None
    work_package_ids: list[str]
    provenance: SourceRef


class ScheduleProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cycles: list[Cycle]
    milestones: list[Milestone]
    effective_weeks_per_cycle: int | None
    roadmap_owner_ids: dict[str, list[str]]
    roadmap_cycle_ids: dict[str, list[str]]
    provenance: list[SourceRef]
