"""Unified offline view. No persistent management or execution state."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .diagnostics import Diagnostic, ordered
from .enums import Severity
from .loader import load
from .parsers.wbs import Catalog
from .rendering import summary
from .validators.wbs import validate
from .validators.schedule import validate_schedule
from .validators.dependencies import validate_dependencies, hard_cycle
from .validators.requirements import validate_requirements

PARSER_VERSION = "offline-project-v1"


@dataclass
class ProjectModel:
    catalog: Catalog
    source_manifest: dict[str, str]

    def diagnostics(self) -> list[Diagnostic]:
        result = validate(self.catalog)
        if self.catalog.schedule is not None:
            result.extend(validate_schedule(self.catalog, self.catalog.schedule))
        if self.catalog.dependencies is not None:
            result.extend(validate_dependencies(self.catalog.dependencies))
            nodes = {n.id for n in self.catalog.dependencies.nodes}
            edges = {e.id for e in self.catalog.dependencies.edges}
            for wp in self.catalog.work_packages:
                for identity, known in [(r, nodes) for r in wp.readiness_refs or []] + [(r, edges) for r in wp.dependency_refs or []]:
                    if identity not in known:
                        result.append(Diagnostic(code="WBS_DEPENDENCY_REFERENCE", severity=Severity.ERROR,
                                                 message=f"Unknown dependency/readiness identity: {identity}", record_id=wp.id, source=wp.provenance))
        if self.catalog.requirements is not None:
            result.extend(validate_requirements(self.catalog, self.catalog.requirements))
        return ordered(result)

    def summary(self) -> dict:
        c = self.catalog
        payload = summary(c, self.diagnostics())
        payload.update(parser=PARSER_VERSION, source_manifest=self.source_manifest)
        if c.schedule:
            scheduled = {wp for cycle in c.schedule.cycles for wp in cycle.work_package_ids}
            payload.update(cycle_count=len(c.schedule.cycles), milestone_count=len(c.schedule.milestones),
                           scheduled_wp_count=len(scheduled), unscheduled_wp_ids=sorted({wp.id for wp in c.work_packages} - scheduled))
        if c.dependencies:
            payload.update(dependency_node_count=len(c.dependencies.nodes), dependency_edge_count=len(c.dependencies.edges),
                           hard_edge_count=sum(e.blocking for e in c.dependencies.edges), soft_edge_count=sum(not e.blocking for e in c.dependencies.edges),
                           hard_cycle_count=int(hard_cycle(c.dependencies.edges) is not None))
        if c.requirements:
            payload.update(requirement_count=len(c.requirements.requirements), fr_count=sum(r.kind == "FR" for r in c.requirements.requirements),
                           nfr_count=sum(r.kind == "NFR" for r in c.requirements.requirements))
        return payload

    def snapshot(self) -> dict:
        c = self.catalog
        return {
            "source": c.source_path, "parser_version": PARSER_VERSION, "source_manifest": self.source_manifest,
            "execution_status": "UNAVAILABLE (documentation only)",
            "capability_areas": [a.model_dump(mode="json") for a in c.capability_areas],
            "work_packages": [wp.model_dump(mode="json") for wp in c.work_packages],
            "schedule": c.schedule.model_dump(mode="json") if c.schedule else None,
            "dependency_nodes": [n.model_dump(mode="json") for n in c.dependencies.nodes] if c.dependencies else None,
            "dependency_edges": [e.model_dump(mode="json") for e in c.dependencies.edges] if c.dependencies else None,
            "requirements": [r.model_dump(mode="json") for r in c.requirements.requirements] if c.requirements else None,
            "trace_overlays": [t.model_dump(mode="json") for t in c.requirements.traces] if c.requirements else None,
            "diagnostics": [d.model_dump(mode="json") for d in self.diagnostics()],
        }


def load_project(root: Path) -> ProjectModel:
    catalog = load(root)
    paths = ["docs/01_Master_Project_Specification.md", "docs/03_Requirements_Traceability_Matrix.md",
             "docs/04_Work_Breakdown_Structure.md", "docs/05_Dependency_Graph.md",
             "docs/06A_Asrin_Engineering_Roadmap.md", "docs/06B_Selman_Engineering_Roadmap.md",
             "docs/06C_Batu_Engineering_Roadmap.md", "docs/06D_Yavuz_Engineering_Roadmap.md", "docs/07_Milestone_and_Release_Plan.md"]
    return ProjectModel(catalog=catalog, source_manifest={p: sha256((root / p).read_bytes()).hexdigest() for p in sorted(paths) if (root / p).is_file()})
