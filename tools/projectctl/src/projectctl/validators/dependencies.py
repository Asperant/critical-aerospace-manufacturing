from collections import Counter, defaultdict
import re

from ..dependency_models import Strength, Kind
from ..diagnostics import Diagnostic
from ..enums import Severity
from ..models import resolve_owner


def hard_cycle(edges):
    adjacency = defaultdict(list)
    for edge in edges:
        if edge.blocking:
            adjacency[edge.predecessor.node].append(edge.successor.node)
    visited, active, path = set(), set(), []
    def visit(node):
        if node in active:
            return path[path.index(node):] + [node]
        if node in visited:
            return None
        active.add(node)
        path.append(node)
        for target in sorted(adjacency.get(node, [])):
            witness = visit(target)
            if witness:
                return witness
        path.pop()
        active.remove(node)
        visited.add(node)
        return None
    for node in sorted(adjacency):
        witness = visit(node)
        if witness:
            return witness
    return None


def validate_dependencies(graph):
    diagnostics = []
    def issue(code, message, edge=None, severity=Severity.ERROR):
        diagnostics.append(Diagnostic(code=code, severity=severity, message=message,
                                      record_id=edge.id if edge else None, source=edge.provenance if edge else None))
    nodes = {n.id: n for n in graph.nodes}
    edges = {e.id: e for e in graph.edges}
    for collection, expected, prefix in [(graph.nodes, 100, "NODE"), (graph.edges, 217, "EDGE")]:
        counts = Counter(x.id for x in collection)
        if len(collection) != expected or len(counts) != expected:
            issue(f"{prefix}_COUNT", f"Expected {expected} unique records; observed {len(collection)} rows, {len(counts)} unique")
        for identity, count in counts.items():
            if count != 1:
                issue(f"DUPLICATE_{prefix}", identity)
    strengths = Counter(e.semantics.strength for e in graph.edges)
    if strengths != {Strength.HARD: 208, Strength.SOFT: 9}:
        issue("STRENGTH_COUNTS", f"Expected HARD 208 / SOFT 9; observed {dict(strengths)}")
    witness = hard_cycle(graph.edges)
    if witness:
        issue("HARD_CYCLE", " → ".join(witness))
    for node in graph.nodes:
        if not re.fullmatch(r"(?:DN|MS|CK)-[A-Z0-9-]+", node.id):
            issue("NODE_ID", node.id)
        if node.type not in {"MILESTONE", "CHECKPOINT"} and resolve_owner(node.raw_owner).canonical_name is None:
            issue("NODE_OWNER", f"Unknown owner on {node.id}: {node.raw_owner}")
    for edge in graph.edges:
        if not re.fullmatch(r"DEP-\d{3}", edge.id):
            issue("EDGE_ID", "Invalid edge identity", edge)
        for endpoint in [edge.predecessor, edge.successor]:
            if endpoint.node not in nodes:
                issue("EDGE_ENDPOINT", f"Unknown endpoint: {endpoint.node}", edge)
            elif endpoint.owner != nodes[endpoint.node].raw_owner:
                issue("EDGE_OWNER", f"Endpoint owner conflicts with node registry: {endpoint.node}", edge)
        predecessor = nodes.get(edge.predecessor.node)
        readiness = edge.semantics.required_readiness
        if predecessor and readiness and readiness not in predecessor.readiness_levels:
            issue("READINESS_INCOMPATIBLE", f"Required {readiness}; declared ladder {predecessor.raw_readiness}; no execution authorization inferred", edge, Severity.WARNING)
        if edge.blocking and not edge.unblock_evidence:
            issue("UNBLOCK_EVIDENCE", "HARD edge has no unblock evidence expectation", edge)
        if edge.blocking and edge.precise_requirement is None:
            issue("PRECISION_MISSING", "Precise requirement absent; section 23's general justification is retained but not certified", edge, Severity.WARNING)
        if edge.fallback == "F1" and edge.semantics.kind != Kind.CONTRACT:
            issue("FIXTURE_SEMANTICS", "F1 declared on non-CONTRACT edge; cannot authorize satisfaction", edge, Severity.WARNING)
        if any(token in edge.need_by for token in ["→", "/", "–", "R2/S"]):
            issue("NEED_BY_AMBIGUOUS", f"Unresolved need-by expression retained: {edge.need_by}", edge, Severity.WARNING)
    registry_counts = Counter(r[0] for r in graph.registry_rows)
    if registry_counts != Counter(e.id for e in graph.edges):
        issue("EDGE_REGISTRY_IDENTITIES", "Registry rows and YAML record identities differ")
    for row in graph.registry_rows:
        edge = edges.get(row[0])
        if edge is None:
            continue
        expected = [edge.id, f"{edge.predecessor.node} → {edge.successor.node}", edge.semantics.kind.value,
                    edge.semantics.strength.value, edge.semantics.blocking_stage.value,
                    edge.semantics.required_readiness.value if edge.semantics.required_readiness else "—", edge.need_by,
                    edge.predecessor.owner, edge.successor.owner, edge.fallback or "—", edge.unblock_evidence, edge.risk_class or "—"]
        if row != expected:
            issue("EDGE_REGISTRY_CONFLICT", "Registry row and YAML disagree", edge)
    return diagnostics
