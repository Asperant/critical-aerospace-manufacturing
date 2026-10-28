import pytest

from projectctl.parsers.dependencies import parse_dependencies, PATH
from projectctl.validators.dependencies import validate_dependencies, hard_cycle
from projectctl.dependency_models import Endpoint, Strength
from projectctl.enums import Severity


@pytest.fixture
def graph(root):
    return parse_dependencies((root / PATH).read_text())


def test_dependency_baseline_and_findings(graph):
    assert len(graph.nodes) == 100 and len(graph.edges) == 217
    assert sum(e.blocking for e in graph.edges) == 208
    assert sum(not e.blocking for e in graph.edges) == 9
    assert hard_cycle(graph.edges) is None
    findings = validate_dependencies(graph)
    assert not [d for d in findings if d.severity == Severity.ERROR]
    assert {d.record_id for d in findings if d.code == "READINESS_INCOMPATIBLE"} == set()
    # CHG-055 and the later approved precision bindings changed the canonical
    # warning set without changing the graph shape. Keep this count as a
    # diagnostic baseline; all diagnostic identities remain fail-closed below.
    assert len([d for d in findings if d.code == "PRECISION_MISSING"]) == 164
    assert {d.record_id for d in findings if d.code == "FIXTURE_SEMANTICS"} == set()


def test_cycle_witness_and_soft_nonblocking(graph):
    edge = graph.edges[0]
    reverse = edge.model_copy(update={"predecessor": edge.successor, "successor": edge.predecessor})
    witness = hard_cycle([edge, reverse])
    assert witness[0] == witness[-1] and set(witness) == {edge.predecessor.node, edge.successor.node}
    soft = reverse.model_copy(update={"semantics": reverse.semantics.model_copy(update={"strength": Strength.SOFT})})
    assert not soft.blocking
    assert hard_cycle([edge, soft]) is None


def test_duplicate_and_endpoint_conflict(graph):
    graph.nodes.append(graph.nodes[0])
    edge = graph.edges[0]
    graph.edges.append(edge.model_copy(update={"successor": Endpoint(node="DN-MISSING", owner="Team")}))
    codes = {d.code for d in validate_dependencies(graph)}
    assert {"DUPLICATE_NODE", "DUPLICATE_EDGE", "EDGE_ENDPOINT"} <= codes


def test_yaml_duplicate_keys_rejected(root):
    text = (root / PATH).read_text().replace("DEP-002:\n", "DEP-001:\n", 1)
    with pytest.raises(ValueError, match="Duplicate YAML key"):
        parse_dependencies(text)


def test_need_by_keeps_ambiguity(graph):
    edge = next(e for e in graph.edges if e.id == "DEP-002")
    assert edge.need_by == "M0→M1"
    assert any(d.code == "NEED_BY_AMBIGUOUS" and d.record_id == edge.id for d in validate_dependencies(graph))


def test_reintroduced_readiness_and_fixture_findings_are_detected(graph):
    # Recreate the former document defects; reconciliation must not weaken validation.
    from projectctl.dependency_models import Readiness
    node = next(n for n in graph.nodes if n.id == "DN-VIS-MODELS")
    graph.nodes[graph.nodes.index(node)] = node.model_copy(update={
        "readiness_levels": [r for r in node.readiness_levels if r != Readiness.INTEGRATION_READY]
    })
    fixture_ids = {"DEP-025", "DEP-045", "DEP-058", "DEP-076", "DEP-094"}
    graph.edges[:] = [e.model_copy(update={"fallback": "F1"}) if e.id in fixture_ids else e for e in graph.edges]
    findings = validate_dependencies(graph)
    assert {d.record_id for d in findings if d.code == "READINESS_INCOMPATIBLE"} == {"DEP-060", "DEP-194"}
    assert {d.record_id for d in findings if d.code == "FIXTURE_SEMANTICS"} == fixture_ids
