"""Bounded, explicitly approved WP import; canonical data is always regenerated.

No sync command, persistent execution store, updates, deletes or invitations.
The terminal cycle policy applies only to Plane's coordination projection.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from html.parser import HTMLParser
import json

from .plane import PlaneError, PlaneReader
from .plane_plan import VISIBLE_ID, WP_ID, _description, bootstrap_plan

POLICY = "human-approved-terminal-target-completion-v1"
ASRIN = "Asrın Dündar"
UNSCHEDULED = ["WP-R2-001", "WP-R2-002", "WP-R2-003", "WP-S-001", "WP-X-001"]
MILESTONES = {"M0": 2, "M1": 14, "M2": 21, "M3": 27, "M4": 39,
              "M5": 30, "M6": 17, "M7": 15, "M8": 10}


class _MetadataHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.current = [], None
        self.code = None

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            if self.current is not None:
                raise PlaneError("Nested canonical metadata block")
            self.current = []
            self.code = None
        elif tag == "code" and self.current is not None:
            if self.code is not None or "".join(self.current).strip():
                raise PlaneError("Unexpected canonical code wrapper")
            self.code = "open"
        elif self.current is not None:
            raise PlaneError("Unexpected markup inside canonical metadata")

    def handle_endtag(self, tag):
        if tag == "code" and self.current is not None:
            if self.code != "open":
                raise PlaneError("Unmatched canonical code wrapper")
            self.code = "closed"
        elif tag == "pre" and self.current is not None:
            if self.code == "open":
                raise PlaneError("Unclosed canonical code wrapper")
            self.blocks.append("".join(self.current))
            self.current = None
        elif self.current is not None:
            raise PlaneError("Unexpected closing markup inside canonical metadata")

    def handle_data(self, data):
        if self.current is not None:
            if self.code == "closed" and data.strip():
                raise PlaneError("Content outside canonical code wrapper")
            self.current.append(data)

    def handle_comment(self, data):
        if self.current is not None:
            raise PlaneError("Unexpected non-data markup inside canonical metadata")

    handle_decl = handle_pi = unknown_decl = handle_comment


def canonical_metadata(description):
    """Compare structured content after server HTML escaping/wrapping, not bytes."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PlaneError("Duplicate canonical metadata key")
            result[key] = value
        return result
    try:
        if isinstance(description, str) and description.lstrip().startswith("{"):
            payload = description  # Explicit raw JSON object; never strip arbitrary HTML.
        else:
            parser = _MetadataHTML()
            parser.feed(description)
            parser.close()
            if len(parser.blocks) != 1 or parser.current is not None:
                raise PlaneError("Expected exactly one complete canonical metadata block")
            payload = parser.blocks[0]
        data = json.loads(payload, object_pairs_hook=unique)
        if not isinstance(data, dict):
            raise PlaneError("Invalid canonical metadata shape")
        return data
    except (TypeError, ValueError):
        raise PlaneError("Canonical metadata HTML/JSON contract mismatch") from None


def identity_index(items, canonical_ids):
    result = {}
    for item in items:
        match = VISIBLE_ID.match(item.get("name", ""))
        visible = match.group(1) if match else None
        external = item.get("external_id")
        if (visible != external or not isinstance(external, str) or not WP_ID.fullmatch(external)
                or external not in canonical_ids or item.get("external_source") != "projectctl"):
            raise PlaneError("Unexpected or conflicting canonical issue identity: " + item["id"])
        if external in result:
            raise PlaneError("Duplicate canonical issue identity: " + external)
        result[external] = item
    return result


def expected_projection(project, audit):
    """Pure exact preview, with the explicitly approved policy separate from sources."""
    base = bootstrap_plan(project, audit)
    if base["conflicts"] or base["unmanaged_work_items"]:
        raise PlaneError("Conflicting Plane inventory; WP import withheld")
    structures = [o for o in base["operations"] if o["kind"] != "work_items"]
    if len(structures) != 52 or any(o["action"] != "unchanged" for o in structures):
        raise PlaneError("Structural baseline drift; WP import cannot change structures")
    if (len(audit["modules"]) != 29 or len(audit["cycles"]) != 13 or len(audit["labels"]) != 10
            or any(c.get("start_date") is not None or c.get("end_date") is not None for c in audit["cycles"])):
        raise PlaneError("Unexpected structures or invented cycle dates")
    asrin = base["owner_mapping"].get(ASRIN)
    if not asrin:
        raise PlaneError("Exact Asrın project membership required")
    modules = {r["name"]: r["id"] for r in audit["modules"]}
    cycles = {r["name"]: r["id"] for r in audit["cycles"]}
    labels = {r["name"]: r["id"] for r in audit["labels"]}
    backlog = next(s["id"] for s in audit["states"] if s["name"] == "BACKLOG")
    wps = {w.id: w for w in project.catalog.work_packages}
    projected = []
    for op in sorted((o for o in base["operations"] if o["kind"] == "work_items"), key=lambda o: o["identity"]):
        w = wps[op["identity"]]
        metadata = dict(op["canonical_metadata"])
        ids = metadata["cycle_ids"]
        terminal = max(ids, key=lambda s: int(s[1:])) if ids else None
        metadata.update(canonical_sprint_window=w.sprint_window, raw_planning_window=w.raw_planning_window,
                        PrimaryOwner=metadata["canonical_owner"],
                        plane_cycle_projection={"policy": POLICY, "coordination_cycle": terminal,
                                                "meaning": "coordination / target-completion projection; canonical full window remains authoritative"})
        body = {"name": op["desired"]["name"], "external_id": w.id, "external_source": "projectctl",
                "description_html": _description(metadata), "state": backlog,
                "assignees": [asrin] if metadata["canonical_owner"] == ASRIN else [],
                "labels": [labels["MS:" + w.milestone]] if w.milestone in MILESTONES else []}
        projected.append({"wp_id": w.id, "metadata": metadata, "create_body": body,
                          "module_id": modules[w.capability_area],
                          "cycle_id": cycles[terminal] if terminal else None})
    single = sum(len(o["metadata"]["cycle_ids"]) == 1 for o in projected)
    multi = sum(len(o["metadata"]["cycle_ids"]) > 1 for o in projected)
    unscheduled = [o["wp_id"] for o in projected if not o["cycle_id"]]
    distribution = Counter(o["metadata"]["milestone"] for o in projected if o["create_body"]["labels"])
    if (len(projected) != 180 or single != 58 or multi != 117 or unscheduled != UNSCHEDULED
            or dict(distribution) != MILESTONES
            or sum(bool(o["create_body"]["assignees"]) for o in projected) != 74):
        raise PlaneError("Canonical approved import invariants failed; no count correction permitted")
    pilot = next(o["wp_id"] for o in projected if o["metadata"]["canonical_owner"] == ASRIN
                 and len(o["metadata"]["cycle_ids"]) == 1 and o["create_body"]["labels"])
    return {"schema_version": "plane-wp-projection-v1", "api_version": "v1", "policy": POLICY,
            "source_manifest": project.source_manifest,
            "control_registry": [s.model_dump() for s in project.control_items], "pilot_wp_id": pilot, "projections": projected,
            "missing_owners": base["missing_owners"], "assignment_policy": "74 exact Asrın assignments; 106 unassigned",
            "semantic_end_state": {"work_items": 180, "modules": 180, "cycles": 175, "milestones": 175, "assignees": 74},
            "single_cycle": single, "multi_cycle": multi, "unscheduled_ids": unscheduled,
            "milestone_distribution": dict(sorted(distribution.items()))}


def check_issue(item, expected):
    body = expected["create_body"]
    for field in ("name", "external_id", "external_source", "state"):
        if item.get(field) != body[field]:
            raise PlaneError(f"{expected['wp_id']}: issue contract mismatch in {field}; no automatic repair")
    for field in ("labels", "assignees"):
        values = item.get(field)
        if not isinstance(values, list) or sorted(values) != sorted(body[field]):
            raise PlaneError(f"{expected['wp_id']}: issue contract mismatch in {field}; no automatic repair")
    if canonical_metadata(item.get("description_html")) != expected["metadata"]:
        raise PlaneError(expected["wp_id"] + ": canonical metadata round-trip mismatch")
    if item.get("parent") is not None:
        raise PlaneError(expected["wp_id"] + ": unexpected sub-item relationship")


def import_plan(projection, inventory):
    """No mutation; all updates and conflicting relationships fail closed."""
    expected = projection["projections"]
    from .control_plane import ControlItem, canonical_audit
    registry = [ControlItem.model_validate(s) for s in projection.get("control_registry", [])]
    audit, controls = canonical_audit(inventory["audit"], registry)
    for item in controls:
        if any(inventory["memberships"][f].get(item["id"], []) for f in ("modules", "cycles")):
            raise PlaneError("Control-only Plane item has module/cycle relationship")
    index = identity_index(audit["work_items"], {e["wp_id"] for e in expected})
    operations, conflicts = [], []
    for e in expected:
        item = index.get(e["wp_id"])
        missing = []
        try:
            if item:
                check_issue(item, e)
                for family, target in [("modules", e["module_id"]), ("cycles", e["cycle_id"])]:
                    actual = inventory["memberships"][family].get(item["id"], [])
                    if actual and actual != ([target] if target else []):
                        raise PlaneError(e["wp_id"] + ": unexpected/multiple " + family + " memberships")
                    if target and not actual:
                        missing.append(family)
            else:
                missing = ["work_items", "modules"] + (["cycles"] if e["cycle_id"] else [])
        except PlaneError as error:
            conflicts.append({"wp_id": e["wp_id"], "diagnostic": str(error)})
        operations.append({"wp_id": e["wp_id"], "plane_id": item["id"] if item else None,
                           "action": "conflict" if conflicts and conflicts[-1]["wp_id"] == e["wp_id"]
                           else "create" if missing else "unchanged", "missing": missing})
    counts = Counter(f for o in operations for f in o["missing"])
    new = [e for e in expected if e["wp_id"] not in index]
    return {"schema_version": "plane-wp-import-plan-v1", "dry_run": True, "policy": POLICY,
            "operations": operations, "conflicts": conflicts, "updates": 0,
            "creates": {f: counts[f] for f in ("work_items", "modules", "cycles")},
            "embedded_milestones": sum(bool(e["create_body"]["labels"]) for e in new),
            "embedded_assignees": sum(bool(e["create_body"]["assignees"]) for e in new),
            "http_mutation_requests": sum(counts.values()),
            "unchanged": sum(o["action"] == "unchanged" for o in operations)}


class ImportFailure(PlaneError):
    def __init__(self, diagnostic, report):
        super().__init__(diagnostic)
        self.report = report


class WPImport:
    def __init__(self, config, project, *, approved=False, transport=None):
        if not approved:
            raise PlaneError("Explicit WP_IMPORT_POLICY approval required")
        self.reader = PlaneReader(config, transport)
        self.project = project
        self.prefix = f"workspaces/{config.workspace_slug}/projects/{config.project_id}/"
        self.report = {"control_item": "CTRL-PM-009", "api_version": "v1", "policy": POLICY,
                       "mutations": [], "reconciliations": [], "verified_wps": [], "result": "INCOMPLETE"}
        self.projection = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.reader.stream.close()

    def inventory(self, *, relations=False):
        audit = self.reader.audit()
        project = self.reader._get(self.prefix)
        if "default_assignee" not in project or project["default_assignee"] is not None:
            raise PlaneError("Project default assignee would violate approved unassigned policy")
        memberships = {}
        for family, route in [("modules", "module-issues"), ("cycles", "cycle-issues")]:
            index = defaultdict(list)
            for entity in audit[family]:
                for item in self.reader._list(self.prefix + f"{family}/{entity['id']}/{route}/"):
                    index[item["id"]].append(entity["id"])
            memberships[family] = dict(index)
        links = {}
        if relations:
            for item in audit["work_items"]:
                # Installed v1 names this route work-items; issues is its supported alias.
                data = self.reader._get(self.prefix + f"work-items/{item['id']}/relations/")
                if not isinstance(data, dict) or not data or any(not isinstance(v, list) for v in data.values()):
                    raise PlaneError("Unexpected issue-relation audit shape")
                links[item["id"]] = data
                if any(data.values()):
                    raise PlaneError("Unexpected blocker/dependency/other issue relations")
        return {"audit": audit, "memberships": memberships, "issue_relations": links,
                "project_default_assignee": project.get("default_assignee")}

    def prepare(self):
        inventory = self.inventory()
        self.projection = expected_projection(self.project, inventory["audit"])
        self.allowed = {e["wp_id"]: e for e in self.projection["projections"]}
        self.report["before"] = inventory
        self.working_inventory = deepcopy(inventory)
        self.report["projection"] = self.projection
        plan = import_plan(self.projection, inventory)
        if plan["conflicts"]:
            raise PlaneError("Import preflight conflicts: " + json.dumps(plan["conflicts"], ensure_ascii=False))
        self.report["preview"] = plan
        return plan

    def _write(self, suffix, body, wp_id, attempt):
        expected = self.allowed.get(wp_id)
        permitted = expected is not None and (
            suffix == "issues/" and body == expected["create_body"] or
            suffix == f"modules/{expected['module_id']}/module-issues/" and set(body) == {"issues"} or
            expected["cycle_id"] and suffix == f"cycles/{expected['cycle_id']}/cycle-issues/" and set(body) == {"issues"})
        if not permitted or suffix != "issues/" and body != {"issues": [self.issue_id]}:
            raise PlaneError("Mutation outside approved WP import scope")
        entry = {"wp_id": wp_id, "method": "POST", "path": "/api/v1/" + self.prefix + suffix,
                 "body": body, "attempt": attempt}
        self.report["mutations"].append(entry)
        try:
            response = self.reader.stream.request("POST", self.prefix + suffix, json=body, attempt=attempt)
        except PlaneError:
            entry["outcome"] = "AMBIGUOUS_TRANSPORT"
            return None
        entry["status"] = response.status_code
        if response.status_code in {200, 201}:
            entry["outcome"] = "ACCEPTED_PENDING_READ"
            try:
                data = response.json()
                entry["response_entity_id"] = data.get("id") if isinstance(data, dict) else None
            except ValueError:
                entry["outcome"] = "AMBIGUOUS_JSON"
            return entry
        if response.status_code in {409, 429} or response.status_code >= 500:
            entry["outcome"] = "AMBIGUOUS_HTTP"
            self.reader.stream.defer(min(2 ** attempt, 30))
            return None
        entry["outcome"] = "REJECTED"
        raise PlaneError(f"WP import POST rejected: HTTP {response.status_code} (body redacted)")

    def _issues(self):
        from .control_plane import canonical_audit
        audit = dict(self.working_inventory["audit"])
        audit["work_items"] = self.reader._list(self.prefix + "issues/")
        canonical, _ = canonical_audit(audit, self.project.control_items)
        return identity_index(canonical["work_items"], set(self.allowed))

    def _create(self, expected):
        wp_id = expected["wp_id"]
        for attempt in range(1, 6):
            index = self._issues()  # Fresh stable-ID inventory; duplicates stop before POST.
            if wp_id in index:
                check_issue(index[wp_id], expected)
                return index[wp_id]
            project = self.reader._get(self.prefix)
            if "default_assignee" not in project or project["default_assignee"] is not None:
                raise PlaneError("Project default assignee changed; create withheld")
            write = self._write("issues/", expected["create_body"], wp_id, attempt)
            index = self._issues()
            if wp_id in index:
                item = self.reader._get(self.prefix + f"issues/{index[wp_id]['id']}/")
                check_issue(item, expected)
                if write and write.get("response_entity_id") and write["response_entity_id"] != item["id"]:
                    raise PlaneError("Issue-create response identity differs from read-back")
                ambiguous = write is None or write["outcome"] == "AMBIGUOUS_JSON"
                self.report["mutations"][-1].update(outcome="VERIFIED", entity_id=item["id"])
                if ambiguous:
                    self.report["reconciliations"].append({"wp_id": wp_id, "kind": "work_items", "result": "PERSISTED"})
                return item
            if write is not None and write["outcome"] == "ACCEPTED_PENDING_READ":
                raise PlaneError("Accepted issue create missing from fresh inventory")
            self.report["reconciliations"].append({"wp_id": wp_id, "kind": "work_items", "result": "ABSENT", "attempt": attempt})
        raise PlaneError("Issue create reconciliation exhausted after 5 attempts")

    def _relationship(self, expected, family, inventory):
        target = expected["module_id" if family == "modules" else "cycle_id"]
        actual = inventory["memberships"][family].get(self.issue_id, [])
        if actual and actual != ([target] if target else []):
            raise PlaneError(expected["wp_id"] + ": conflicting relationship; no automatic moves")
        if not target:
            return
        route = "module-issues" if family == "modules" else "cycle-issues"
        suffix = f"{family}/{target}/{route}/"
        for attempt in range(1, 6):
            rows = self.reader._list(self.prefix + suffix)
            if any(r["id"] == self.issue_id for r in rows):
                return
            write = self._write(suffix, {"issues": [self.issue_id]}, expected["wp_id"], attempt)
            rows = self.reader._list(self.prefix + suffix)
            if any(r["id"] == self.issue_id for r in rows):
                ambiguous = write is None or write["outcome"] == "AMBIGUOUS_JSON"
                self.report["mutations"][-1].update(outcome="VERIFIED", entity_id=self.issue_id, relationship_id=target)
                inventory["memberships"][family][self.issue_id] = [target]
                if ambiguous:
                    self.report["reconciliations"].append({"wp_id": expected["wp_id"], "kind": family, "result": "PERSISTED"})
                    fresh = self.inventory()
                    if fresh["memberships"][family].get(self.issue_id) != [target]:
                        raise PlaneError("Ambiguous relationship produced multiple/conflicting memberships")
                return
            if write is not None and write["outcome"] == "ACCEPTED_PENDING_READ":
                raise PlaneError("Accepted relationship missing from fresh read-back")
            fresh = self.inventory()
            if fresh["memberships"][family].get(self.issue_id):
                raise PlaneError("Conflicting relationship after ambiguous write")
            self.report["reconciliations"].append({"wp_id": expected["wp_id"], "kind": family, "result": "ABSENT", "attempt": attempt})
        raise PlaneError("Relationship reconciliation exhausted after 5 attempts")

    def apply_one(self, wp_id):
        e = self.allowed[wp_id]
        item = self._create(e)
        self.issue_id = item["id"]
        inventory = self.working_inventory
        self._relationship(e, "modules", inventory)
        self._relationship(e, "cycles", inventory)
        fresh = self.reader._get(self.prefix + f"issues/{self.issue_id}/")
        check_issue(fresh, e)
        self.report["verified_wps"].append({"wp_id": wp_id, "plane_id": self.issue_id,
                                            "module_id": e["module_id"], "cycle_id": e["cycle_id"],
                                            "labels": fresh["labels"], "assignees": fresh["assignees"]})

    def audit(self):
        fresh = self.inventory(relations=True)
        projection = expected_projection(self.project, fresh["audit"])
        if projection != self.projection:
            raise PlaneError("Structures/member/source projection changed during import")
        plan = import_plan(projection, fresh)
        if plan["conflicts"] or plan["http_mutation_requests"] or plan["unchanged"] != 180:
            raise PlaneError("Full WP import audit failed: " + json.dumps(plan, ensure_ascii=False))
        before = self.report["before"]["audit"]
        for resource in ("states", "labels", "modules", "cycles"):
            if fresh["audit"][resource] != before[resource]:
                raise PlaneError("Unapproved structural drift: " + resource)
        from .control_plane import canonical_audit
        canonical, controls = canonical_audit(fresh["audit"], self.project.control_items)
        index = identity_index(canonical["work_items"], set(self.allowed))
        for family in ("modules", "cycles"):
            if set(fresh["memberships"][family]) - {i["id"] for i in index.values()}:
                raise PlaneError("Unexpected noncanonical relationship member")
        summary = {"result": "PASS", "wp_count": len(index), "control_item_count": len(controls),
                   "total_work_item_count": len(fresh["audit"]["work_items"]), "backlog": len(index), "ready_or_later": 0,
                   "duplicate_canonical_ids": [], "module_relationships": 180, "cycle_relationships": 175,
                   "milestone_relationships": 175, "asrin_assigned": 74, "unassigned": 106,
                   "module_distribution": dict(sorted(Counter(e["metadata"]["capability_area"] for e in projection["projections"]).items())),
                   "owner_distribution": dict(sorted(Counter(e["metadata"]["canonical_owner"] for e in projection["projections"]).items())),
                   "milestone_distribution": projection["milestone_distribution"], "unscheduled_ids": UNSCHEDULED,
                   "single_cycle": 57, "terminal_multi_cycle": 117, "issue_relations": 0,
                   "source_manifest": self.project.source_manifest, "execution_evidence": "NOT ASSERTED"}
        return {"summary": summary, "inventory": fresh, "dry_run": plan}

    def run(self, progress=None, checkpoint=None):
        try:
            self.prepare()
            pilot = self.projection["pilot_wp_id"]
            self.report["pilot_expected"] = self.allowed[pilot]
            if checkpoint:
                checkpoint(self.finish())  # Persist exact preview/pilot before the first POST.
            if self.report["preview"]["http_mutation_requests"] == 0:
                self.report["post_import"] = self.audit()
                self.report["http_mutation_counts"] = {}
                self.report["result"] = "PASS"
                return self.finish()
            self.apply_one(pilot)
            pilot_inventory = self.inventory(relations=True)
            pilot_plan = import_plan(self.projection, pilot_inventory)
            pilot_op = next(o for o in pilot_plan["operations"] if o["wp_id"] == pilot)
            if pilot_plan["conflicts"] or pilot_op["action"] != "unchanged":
                raise PlaneError("Pilot relationship/metadata contract failed")
            self.report["pilot_result"] = {"result": "PASS", "wp_id": pilot, "operation": pilot_op}
            if progress:
                progress(pilot, 1)
            if checkpoint:
                checkpoint(self.finish())
            for count, wp_id in enumerate(sorted(set(self.allowed) - {pilot}), 2):
                self.apply_one(wp_id)
                if progress:
                    progress(wp_id, count)
                if checkpoint:
                    checkpoint(self.finish())
            self.report["post_import"] = self.audit()
            self.report["semantic_end_state"] = self.projection["semantic_end_state"]
            self.report["http_mutation_counts"] = dict(Counter(m["method"] for m in self.report["mutations"]))
            self.report["result"] = "PASS"
            return self.finish()
        except PlaneError as error:
            self.report["error"] = str(error)
            if "pilot_expected" in self.report and "pilot_result" not in self.report:
                self.report["human_gate"] = "BLOCKED_FOR_HUMAN: WP_IMPORT_CONTRACT_MISMATCH"
            raise ImportFailure(str(error), self.finish()) from None

    def finish(self):
        self.report["reads"] = self.reader.reads.copy()
        self.report["request_events"] = self.reader.stream.events.copy()
        return self.report
