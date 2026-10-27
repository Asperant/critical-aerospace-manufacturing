from copy import deepcopy
from pathlib import Path

import pytest

from projectctl.control_plane import (REGISTRY_PATH, canonical_audit, classify_inventory,
                                      load_registry, partition_controls, validate_registry)
from projectctl.plane import PlaneError
from projectctl.plane_import import expected_projection, import_plan
from projectctl.plane_plan import STATES, _description, bootstrap_plan
from projectctl.project import load_project


@pytest.fixture(scope="module")
def project():
    return load_project(Path(__file__).resolve().parents[3])


@pytest.fixture(scope="module")
def inventory(project):
    audit = {"schema_version": "plane-v1-audit-v1", "api_version": "v1", "mutation_enabled": False,
             "workspace": {"slug": "test", "id": "workspace"},
             "project": {"id": "project", "name": "Graduation Project", "identifier": "CAP"},
             "states": [{"id": s, "name": s} for s in STATES], "modules": [], "cycles": [],
                 "labels": [{"id": "blocked", "name": "BLOCKED"}], "work_items": [],
                 "project_members": [
                     {"id": "asrin", "first_name": "Asrın", "last_name": "Dündar"},
                     {"id": "batuhan", "first_name": "Batuhan", "last_name": "Kaya"},
                     {"id": "selman", "first_name": "Selman", "last_name": "Özdemir"},
                     {"id": "yavuz", "first_name": "Yavuz", "last_name": "Gümüş"},
                 ]}
    for op in bootstrap_plan(project, audit)["operations"]:
        if op["kind"] != "work_items" and op["action"] == "create":
            audit[op["kind"]].append({"id": op["identity"], **op["desired"]})
    projection = expected_projection(project, audit)
    memberships = {"modules": {}, "cycles": {}}
    for op in projection["projections"]:
        plane_id = "issue-" + op["wp_id"]
        audit["work_items"].append({"id": plane_id, **op["create_body"], "parent": None})
        memberships["modules"][plane_id] = [op["module_id"]]
        if op["cycle_id"]:
            memberships["cycles"][plane_id] = [op["cycle_id"]]
    spec = project.control_items[0]
    audit["work_items"].append({"id": "pilot", "name": spec.title, "external_id": spec.control_id,
                               "external_source": spec.external_source,
                               "description_html": _description(spec.metadata()), "state": "IN_PROGRESS",
                               "assignees": ["asrin"], "labels": [], "parent": None, "cycle": None})
    return {"audit": audit, "memberships": memberships}, projection


def test_control_is_exactly_separate_from_180_and_import_noop(project, inventory):
    data, projection = deepcopy(inventory)
    report = classify_inventory(project, data["audit"], memberships=data["memberships"], require_controls=True)
    assert (report["canonical_wp_count"], report["control_item_count"], report["total_work_item_count"]) == (180, 1, 181)
    assert report["canonical_assigned"] == 180 and report["canonical_unassigned"] == 0
    assert report["canonical_owner_distribution"] == {"Asrın Dündar": 74, "Selman Özdemir": 17, "Batuhan Kaya": 32, "Yavuz Gümüş": 57}
    plan = import_plan(projection, data)
    assert not plan["conflicts"] and plan["unchanged"] == 180 and plan["http_mutation_requests"] == 0
    bootstrap = bootstrap_plan(project, data["audit"])
    assert bootstrap["control_item_count"] == 1 and bootstrap["unmanaged_work_items"] == []
    assert bootstrap["summary"]["work_packages"] == 180
    assert len(data["audit"]["labels"]) == 10
    assert len(project.catalog.requirements.requirements) == 306


@pytest.mark.parametrize("field,value", [
    ("external_id", "CTRL-PM-015-PILOT-002"), ("name", "[CONTROL] wrong"),
    ("external_source", "projectctl"), ("assignees", ["wrong"]), ("labels", ["blocked"]),
    ("cycle", "S1"), ("module", "WP-PLAT"), ("modules", ["WP-PLAT"]),
    ("parent", "product"), ("state", "BLOCKED"), ("description_html", "<pre>{}</pre>")])
def test_malformed_control_never_excluded(project, inventory, field, value):
    data, _ = deepcopy(inventory)
    data["audit"]["work_items"][-1][field] = value
    with pytest.raises(PlaneError):
        classify_inventory(project, data["audit"])


@pytest.mark.parametrize("kind", ["canonical", "control", "unknown", "missing_canonical", "missing_control"])
def test_unknown_missing_and_duplicate_items_fail(project, inventory, kind):
    data, _ = deepcopy(inventory)
    rows = data["audit"]["work_items"]
    if kind in {"canonical", "control"}:
        item = deepcopy(rows[0 if kind == "canonical" else -1]); item["id"] = "duplicate"
        rows.append(item)
    elif kind == "unknown":
        rows.append({"id": "unknown", "name": "Other ordinary task", "external_id": "OTHER-001"})
    else:
        rows.pop(0 if kind == "missing_canonical" else -1)
    with pytest.raises(PlaneError):
        classify_inventory(project, data["audit"], require_controls=True)


@pytest.mark.parametrize("family", ["modules", "cycles"])
def test_control_relationships_fail_even_if_issue_response_omits_them(project, inventory, family):
    data, projection = deepcopy(inventory)
    data["memberships"][family]["pilot"] = ["unexpected"]
    with pytest.raises(PlaneError):
        classify_inventory(project, data["audit"], memberships=data["memberships"])
    with pytest.raises(PlaneError):
        import_plan(projection, data)


@pytest.mark.parametrize("field,value", [("control_only", False), ("canonical_wp", True), ("control_only", 1)])
def test_control_metadata_flags_are_exact_booleans(project, inventory, field, value):
    data, _ = deepcopy(inventory)
    metadata = project.control_items[0].metadata();metadata[field] = value
    data["audit"]["work_items"][-1]["description_html"] = _description(metadata)
    with pytest.raises(PlaneError):
        classify_inventory(project, data["audit"])


def test_registry_does_not_accept_duplicate_ids_keys_or_broad_extras(project, tmp_path):
    row = project.control_items[0].model_dump()
    with pytest.raises(PlaneError):
        validate_registry({"schema_version": "control-plane-items-v1", "items": [row, row]})
    for change in [{"canonical_wp": True}, {"control_only": 1}, {"module": "WP-PLAT"}, {"unexpected": True}]:
        with pytest.raises(PlaneError):
            validate_registry({"schema_version": "control-plane-items-v1", "items": [{**row, **change}]})
    path = tmp_path / REGISTRY_PATH;path.parent.mkdir()
    path.write_text('schema_version: control-plane-items-v1\nitems: []\nitems: []\n')
    with pytest.raises(PlaneError, match="Duplicate"):
        load_registry(tmp_path)


def test_unknown_controls_are_not_accepted_by_prefix_or_title(project, inventory):
    data, _ = deepcopy(inventory)
    row = data["audit"]["work_items"][-1]
    row["external_id"] = "CTRL-PM-999-PILOT-001"
    row["name"] = "[CONTROL] CTRL-PM-999-PILOT-001"
    with pytest.raises(PlaneError, match="Unknown control"):
        partition_controls(data["audit"], project.control_items)


def test_control_metadata_reuses_pre_code_parser_and_never_mutates_input(project, inventory):
    data, _ = deepcopy(inventory)
    original = deepcopy(data)
    row = data["audit"]["work_items"][-1]
    row["description_html"] = row["description_html"].replace('<pre>', '<pre><code>').replace('</pre>', '</code></pre>')
    filtered, controls = canonical_audit(data["audit"], project.control_items)
    assert len(filtered["work_items"]) == 180 and len(controls) == 1
    assert data["audit"]["work_items"][:-1] == original["audit"]["work_items"][:-1]
    assert len(data["audit"]["work_items"]) == 181


@pytest.mark.parametrize("change", [{"external_id": []}, {"name": None}])
def test_invalid_identity_shapes_fail_closed(project, inventory, change):
    data, _ = deepcopy(inventory)
    data["audit"]["work_items"][-1].update(change)
    with pytest.raises(PlaneError):
        classify_inventory(project, data["audit"])


def test_duplicate_plane_entity_id_fails_even_across_classes(project, inventory):
    data, _ = deepcopy(inventory)
    data["audit"]["work_items"][-1]["id"] = data["audit"]["work_items"][0]["id"]
    with pytest.raises(PlaneError, match="Duplicate Plane"):
        classify_inventory(project, data["audit"])


@pytest.mark.parametrize("change", [{"control_only": True}, {"canonical_wp": False},
                                     {"canonical_wp_id": "WP-WRONG-001"}, {"canonical_owner": "Wrong owner"}])
def test_canonical_metadata_cannot_claim_control_identity(project, inventory, change):
    from projectctl.plane_import import canonical_metadata
    data, _ = deepcopy(inventory)
    row = data["audit"]["work_items"][0]
    metadata = canonical_metadata(row["description_html"])
    metadata.update(change)
    row["description_html"] = _description(metadata)
    with pytest.raises(PlaneError, match="metadata identity collision"):
        classify_inventory(project, data["audit"])


def test_control_owner_must_resolve_uniquely(project, inventory):
    data, _ = deepcopy(inventory)
    data["audit"]["project_members"].append({"id": "other", "first_name": "Asrın", "last_name": "Dündar"})
    with pytest.raises(PlaneError, match="missing or ambiguous"):
        classify_inventory(project, data["audit"])
