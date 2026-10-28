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
    assert len([d for d in findings if d.code == "PRECISION_MISSING"]) == 162
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


KERNEL_SOURCE = "services/manufacturing-simulator/src/manufacturing_simulator"


def kernel_members(root):
    """Method and field names of each kernel class, read from the AST (no import)."""
    import ast

    members = {}
    for module in ("kernel.py", "events.py"):
        tree = ast.parse((root / KERNEL_SOURCE / module).read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            names = members.setdefault(node.name, set())
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    names.add(item.name)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    names.add(item.target.id)
    return members


def test_dep_043_start_predicate_is_the_kernel_not_the_dispatch_deliverable(graph, root):
    """CHG-077: the START edge asks DN-SIM-KERNEL for kernel facts only."""
    edge = next(e for e in graph.edges if e.id == "DEP-043")
    # Only the predicate wording moved; every approved field of the edge is unchanged.
    assert (edge.predecessor.node, edge.predecessor.owner) == ("DN-SIM-KERNEL", "Batu")
    assert (edge.successor.node, edge.successor.owner) == ("DN-SIM-DISPIF", "Batu")
    semantics = edge.semantics
    assert (semantics.kind.value, semantics.strength.value) == ("CAPABILITY", "HARD")
    assert semantics.blocking_stage.value == "START"
    assert semantics.required_readiness.value == "COMPONENT_READY"
    assert (edge.need_by, edge.fallback, edge.risk_class) == ("S2", None, "DR-1")

    # The dispatch interface and baseline are the consumer's own deliverable.
    assert "baseline dispatch interface callable" not in edge.unblock_evidence
    assert "produced and verified by WP-SIM-006" in edge.unblock_evidence
    assert "not a DispatchDecision wire contract" in edge.precise_requirement

    # Every kernel API the precise requirement names exists on current main.
    members = kernel_members(root)
    named = {
        "Kernel": {"register_handler", "schedule", "step", "run"},
        "ExecutionContext": {"now", "stream", "schedule"},
        "EventSpec": {"time", "kind", "payload", "event_id"},
        "ScheduledEvent": {"sequence"},
    }
    for cls, names in named.items():
        assert names <= members[cls], cls
        assert cls in edge.precise_requirement
    for phrase in (
        "register_handler(kind, EventHandler)",
        "schedule(EventSpec)",
        "step()/run(until, max_events)",
        "ExecutionContext.now/stream()/schedule()",
        "immutable execution records",
    ):
        assert phrase in edge.precise_requirement

    # Table row, YAML record and precise-consumer appendix agree.
    findings = validate_dependencies(graph)
    own = {d.code for d in findings if d.record_id == edge.id}
    assert own <= {"NEED_BY_AMBIGUOUS"} and "EDGE_REGISTRY_CONFLICT" not in own
    appendix = [
        line
        for line in (root / PATH).read_text(encoding="utf-8").splitlines()
        if line.startswith("| DEP-043 | DN-SIM-DISPIF at START |")
    ]
    assert len(appendix) == 1 and edge.unblock_evidence in appendix[0]


def test_dep_043_ready_is_bound_to_the_recorded_authority(graph, root):
    """While DEP-043 is READY, CHG-077 and the evidence must carry its authority."""
    import yaml

    edge = next(e for e in graph.edges if e.id == "DEP-043")
    if edge.status == "READY":
        record = yaml.safe_load((root / "09_change/CHG-077.yaml").read_text("utf-8"))
        record = record["CHG-077"]
        assert record["decision"].startswith("APPROVED")
        review = "pull/199#pullrequestreview-5689282669"
        assert review in record["decision_basis"]
        path = root / "evidence/WP-SIM-006/DEP-043-START-READINESS.md"
        evidence = path.read_text("utf-8")
        assert review in evidence
        assert "owner değerlendirmem olarak kabul ediyorum" in evidence


def module_names(root, module):
    """Top-level function, class and constant names of one simulator module (AST)."""
    import ast

    tree = ast.parse((root / KERNEL_SOURCE / module).read_text(encoding="utf-8"))
    names = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            names[node.name] = None
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    names[target.id] = node.value.value
    return names


def test_dep_037_names_the_kernel_and_replay_surface_it_consumes(graph, root):
    """CHG-078: the START edge binds kernel and replay APIs, not OPSEM behaviour."""
    edge = next(e for e in graph.edges if e.id == "DEP-037")
    assert (edge.predecessor.node, edge.successor.node) == ("DN-SIM-KERNEL", "DN-SIM-OPSEM")
    semantics = edge.semantics
    assert (semantics.kind.value, semantics.strength.value) == ("CAPABILITY", "HARD")
    assert semantics.blocking_stage.value == "START"
    assert semantics.required_readiness.value == "COMPONENT_READY"
    assert (edge.need_by, edge.fallback, edge.risk_class) == ("S2", None, "DR-1")
    assert edge.unblock_evidence == "kernel tests + deterministic replay green"

    text = edge.precise_requirement
    assert text and "not part of this START edge" in text

    # Every kernel and replay name the requirement relies on exists on current main.
    members = kernel_members(root)
    assert {"register_handler", "schedule", "step", "run"} <= members["Kernel"]
    assert {"now", "stream", "schedule"} <= members["ExecutionContext"]
    replay = module_names(root, "replay.py")
    assert {"ReplaySpec", "replay", "compare", "check_determinism"} <= set(replay)
    serialization = module_names(root, "serialization.py")
    assert {"event_sequence_digest", "final_state_digest"} <= set(serialization)
    assert serialization["FORMAT_VERSION"] == "sim-replay-hash/1"
    for phrase in (
        "Kernel(WorldState, handlers)",
        "schedule(EventSpec)",
        "ReplaySpec",
        "replay(spec, handlers)",
        "check_determinism",
        "event_sequence_digest",
        "final_state_digest",
        "sim-replay-hash/1",
    ):
        assert phrase in text

    # The named random streams are the registered ones.
    import ast

    tree = ast.parse((root / KERNEL_SOURCE / "rng.py").read_text(encoding="utf-8"))
    streams = {
        node.value.value
        for cls in tree.body
        if isinstance(cls, ast.ClassDef) and cls.name == "StreamName"
        for node in cls.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
    }
    assert {"arrival", "processing", "failure", "repair", "quality", "inspection"} <= streams
    assert "arrival, processing, failure, repair, quality and inspection" in text

    # Table row, YAML record and appendix agree and the edge raises no new finding.
    own = {d.code for d in validate_dependencies(graph) if d.record_id == edge.id}
    assert own <= {"NEED_BY_AMBIGUOUS"}
    appendix = [
        line
        for line in (root / PATH).read_text(encoding="utf-8").splitlines()
        if line.startswith("| DEP-037 | DN-SIM-OPSEM at START |")
    ]
    assert len(appendix) == 1 and edge.unblock_evidence in appendix[0]

    # While READY, the change record and the evidence must carry the authority.
    if edge.status == "READY":
        import yaml

        record = yaml.safe_load((root / "09_change/CHG-078.yaml").read_text("utf-8"))
        assert record["CHG-078"]["decision"].startswith("APPROVED")
        path = root / "evidence/WP-SIM-003/DEP-037-START-READINESS.md"
        assert "## Owner adoption" in path.read_text("utf-8")
