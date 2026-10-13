"""Explicit control-only identity policy; no runtime state or HTTP mutations."""
from collections import Counter
from pathlib import Path
from typing import Literal
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, ValidationError
import yaml

from .plane import PlaneError

REGISTRY_PATH = "project_control/control_plane_items.yaml"
LIFECYCLE = {"BACKLOG", "READY", "IN_PROGRESS", "IN_REVIEW", "MERGE_READY", "MERGED", "VALIDATING", "DONE"}


class ControlItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    control_id: str = Field(pattern=r"^CTRL-[A-Z]+-\d{3}-PILOT-\d{3}$")
    title: str
    external_source: Literal["projectctl-control"]
    control_only: Literal[True]
    canonical_wp: Literal[False]
    related_control: str = Field(pattern=r"^CTRL-[A-Z]+-\d{3}$")
    purpose: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    module: None
    cycle: None
    lifecycle: dict[str, str]
    evidence_expectations: list[str] = Field(min_length=1)

    def metadata(self):
        return self.model_dump(exclude={"title", "external_source", "lifecycle", "evidence_expectations"})


def validate_registry(data):
    if not isinstance(data, dict) or set(data) != {"schema_version", "items"} or data["schema_version"] != "control-plane-items-v1" or not isinstance(data["items"], list):
        raise PlaneError("Invalid control Plane registry")
    try:
        if any(not isinstance(row, dict) or type(row.get("control_only")) is not bool
               or type(row.get("canonical_wp")) is not bool for row in data["items"]):
            raise PlaneError("Control registry flags must be explicit booleans")
        items = [ControlItem.model_validate(row) for row in data["items"]]
    except ValidationError:
        raise PlaneError("Invalid control Plane registry fields") from None
    if len({i.control_id for i in items}) != len(items):
        raise PlaneError("Duplicate control registry identity")
    for item in items:
        if (item.title != f"[CONTROL] {item.control_id} — Governed Lifecycle Rehearsal"
                or not item.control_id.startswith(item.related_control + "-PILOT-")
                or set(item.lifecycle) != LIFECYCLE
                or not all(item.lifecycle.values()) or not all(item.evidence_expectations)
                or type(item.control_only) is not bool or type(item.canonical_wp) is not bool):
            raise PlaneError("Invalid control registry identity/lifecycle contract")
    return items


def load_registry(root: Path):
    path = root / REGISTRY_PATH
    if not path.is_file():
        return []  # Older/offline fixture baselines explicitly allow no control items.
    class UniqueLoader(yaml.SafeLoader):
        pass
    def mapping(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            if key in result:
                raise PlaneError("Duplicate control registry YAML key")
            result[key] = loader.construct_object(value_node)
        return result
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        return validate_registry(yaml.load(path.read_text(), Loader=UniqueLoader))
    except (yaml.YAMLError, TypeError):
        raise PlaneError("Invalid control registry YAML") from None


def owner_id(audit, owner):
    def normalize(name):
        return " ".join(unicodedata.normalize("NFC", name).casefold().split())
    matches = [m for m in audit.get("project_members") or []
               if normalize(m.get("first_name", "") + " " + m.get("last_name", "")) == normalize(owner)]
    if len(matches) != 1:
        raise PlaneError("Control owner project membership missing or ambiguous")
    return matches[0]["id"]


def partition_controls(audit, registry):
    # Reuse the existing strict HTML/JSON parser; no new representation exception.
    from .plane_import import canonical_metadata
    by_id = {s.control_id: s for s in registry}
    canonical, controls, seen, plane_ids = [], [], set(), set()
    for item in audit["work_items"]:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or not isinstance(item.get("name"), str)
                or item.get("external_id") is not None and not isinstance(item["external_id"], str)):
            raise PlaneError("Invalid Plane work-item identity shape")
        if item["id"] in plane_ids:
            raise PlaneError("Duplicate Plane work-item entity ID")
        plane_ids.add(item["id"])
        identity = item.get("external_id")
        candidate = (identity in by_id or item.get("external_source") == "projectctl-control"
                     or item.get("name", "").startswith("[CONTROL]"))
        if not candidate:
            canonical.append(item)
            continue
        if identity not in by_id:
            raise PlaneError("Unknown control-only Plane identity")
        if identity in seen:
            raise PlaneError("Duplicate control-only Plane identity: " + identity)
        seen.add(identity)
        spec = by_id[identity]
        metadata = canonical_metadata(item.get("description_html"))
        if (item.get("name") != spec.title or item.get("external_source") != spec.external_source
                or metadata != spec.metadata()
                or type(metadata.get("control_only")) is not bool or type(metadata.get("canonical_wp")) is not bool
                or item.get("assignees") != [owner_id(audit, spec.owner)]
                or item.get("labels") != [] or item.get("parent") is not None
                or item.get("cycle") is not None or item.get("module") is not None or item.get("modules") not in (None, [])):
            raise PlaneError("Control-only Plane representation mismatch: " + identity)
        states = [s for s in audit["states"] if s.get("id") == item.get("state")]
        if len(states) != 1 or states[0]["name"] not in spec.lifecycle:
            raise PlaneError("Control-only Plane lifecycle state mismatch: " + identity)
        controls.append(item)
    return canonical, controls


def canonical_audit(audit, registry):
    result = dict(audit)
    result["work_items"], controls = partition_controls(audit, registry)
    return result, controls


def classify_inventory(project, audit, *, memberships=None, require_controls=False):
    """Validate exact canonical identities separately from allowlisted controls."""
    from .plane_import import identity_index, canonical_metadata
    canonical, controls = partition_controls(audit, project.control_items)
    expected = {w.id for w in project.catalog.work_packages}
    index = identity_index(canonical, expected)
    if set(index) != expected:
        raise PlaneError("Canonical Plane WP population differs from source registry")
    owners = {}
    wps = {w.id: w for w in project.catalog.work_packages}
    for identity, item in index.items():
        metadata = canonical_metadata(item.get("description_html"))
        expected_owner = wps[identity].primary_owner.canonical_name
        if (metadata.get("canonical_wp_id") != identity or metadata.get("canonical_owner") != expected_owner
                or any(key in metadata for key in ("control_id", "control_only", "canonical_wp", "related_control"))):
            raise PlaneError("Canonical/control metadata identity collision: " + identity)
        owners[identity] = expected_owner
    if require_controls and {i["external_id"] for i in controls} != {s.control_id for s in project.control_items}:
        raise PlaneError("Registered control-only Plane item missing")
    for item in controls:
        if memberships is not None and any(memberships[family].get(item["id"], []) for family in ("modules", "cycles")):
            raise PlaneError("Control-only Plane item has module/cycle relationship")
    return {"canonical_wp_count": len(index), "control_item_count": len(controls),
            "total_work_item_count": len(audit["work_items"]),
            "canonical_owner_distribution": dict(sorted(Counter(owners.values()).items())),
            "canonical_assigned": sum(bool(i.get("assignees")) for i in canonical),
            "canonical_unassigned": sum(not i.get("assignees") for i in canonical),
            "controls": [{"control_id": i["external_id"], "plane_id": i["id"], "state_id": i["state"]} for i in controls]}
