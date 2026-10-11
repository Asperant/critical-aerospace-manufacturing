from dataclasses import dataclass, field
import re

from ..dependency_models import DependencyNode, DependencyEdge, Readiness
from ..provenance import SourceRef
from .markdown import table_cells
from .yaml_blocks import records

PATH = "docs/05_Dependency_Graph.md"


@dataclass
class DependencyGraph:
    nodes: list[DependencyNode] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)
    registry_rows: list[list[str]] = field(default_factory=list)


def parse_dependencies(text):
    graph = DependencyGraph()
    start, end = text.index("## 5. Node Registry"), text.index("## 6. Dependency Registry")
    for offset, line in enumerate(text[start:end].splitlines()):
        row = table_cells(line)
        if not row or not row[0].startswith(("DN-", "MS-", "CK-")):
            continue
        if len(row) != 7:
            raise ValueError(f"Invalid node row: {line}")
        number = text[:start].count("\n") + offset + 1
        levels = [Readiness(part.split("(")[0]) for part in row[4].split("→")] if not row[4].startswith("PASS/FAIL") else []
        graph.nodes.append(DependencyNode(id=row[0], name=row[1], type=row[2], raw_owner=row[3],
                                          readiness_levels=levels, raw_readiness=row[4],
                                          architecture_refs=re.findall(r"\bARCH-[A-Z0-9-]+", row[5]), raw_requirement_refs=row[6],
                                          provenance=SourceRef(path=PATH, heading="5. Node Registry", line_start=number, line_end=number, raw_context=line)))
    for key, data, ref in records(text, PATH, "## 23. Edge Records", "## 24. Machine-Readable"):
        graph.edges.append(DependencyEdge(id=key, provenance=ref, **data))
    region = text[text.index("## 6. Dependency Registry"):text.index("## 7. Platform Dependency Spine")]
    graph.registry_rows = [r for line in region.splitlines() if (r := table_cells(line)) and r[0].startswith("DEP-")]
    graph.nodes.sort(key=lambda n: n.id)
    graph.edges.sort(key=lambda e: e.id)
    return graph
