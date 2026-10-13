"""CTRL-PM-008 only: one approved rename and missing structures. No WP writes."""
from collections import Counter
import re

from .plane import PlaneError, PlaneReader
from .plane_plan import bootstrap_plan

OLD_STATE = "IN_REVİEW"
NEW_STATE = "IN_REVIEW"


class BootstrapFailure(PlaneError):
    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


def _semantic(row):
    # API-managed modification bookkeeping inevitably changes on PATCH.
    return {k: v for k, v in row.items() if k not in {"updated_at", "updated_by"}}


class StructureBootstrap:
    def __init__(self, config, project, approved_state_id, *, approved=False, transport=None):
        if approved is not True:
            raise PlaneError("Explicit CTRL-PM-008 approval required")
        if not re.fullmatch(r"[a-fA-F0-9-]{36}", approved_state_id):
            raise PlaneError("Invalid approved state identity")
        self.config, self.project, self.state_id = config, project, approved_state_id
        self.reader = PlaneReader(config, transport)
        self.prefix = f"workspaces/{config.workspace_slug}/projects/{config.project_id}/"
        self.stream = self.reader.stream
        self.report = {"control_item": "CTRL-PM-008", "api_version": "v1", "result": "INCOMPLETE",
                       "mutations": [], "reads": [], "state_rename": None}
        self.allowed_creates = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.reader.__exit__(*args)

    def _write(self, method, suffix, body, identity):
        # An explicit allowlist prevents issue/member/relationship/date writes.
        allowed = (method == "PATCH" and suffix == f"states/{self.state_id}/" and body == {"name": NEW_STATE}) or (
            method == "POST" and suffix in {"modules/", "cycles/", "labels/"}
            and self.allowed_creates.get((suffix, identity)) == body and set(body) <= {"name", "description"})
        if not allowed:
            raise PlaneError("Mutation outside approved CTRL-PM-008 scope")
        entry = {"method": method, "path": "/api/v1/" + self.prefix + suffix,
                 "identity": identity, "body": body, "outcome": "UNKNOWN"}
        self.report["mutations"].append(entry)
        entry["attempts"] = []
        for attempt in range(1, 6):
            status, data = None, None
            try:
                response = self.stream.request(method, self.prefix + suffix, json=body,
                                               idempotent=method == "PATCH", attempt=attempt)
                status = response.status_code
                entry["http_status"] = status
                try:
                    data = response.json()
                except ValueError:
                    pass
            except PlaneError:
                if method != "POST":
                    raise
            entry["attempts"].append({"attempt": attempt, "http_status": status})
            if status in ({200} if method == "PATCH" else {200, 201}) and isinstance(data, dict) and isinstance(data.get("id"), str):
                entry.update(outcome="ACCEPTED_NOT_VERIFIED", entity_id=data["id"])
                return data
            ambiguous = status is None or status == 429 or status is not None and (status >= 500 or status in {200, 201})
            if method == "POST" and ambiguous:
                # No blind POST replay. Wait, then determine whether the intended create persisted.
                if status != 429:
                    self.stream.defer(min(2 ** attempt, 30))
                matches = [r for r in self._raw(suffix.rstrip("/")) if r.get("name") == identity]
                if len(matches) > 1 or matches and any(matches[0].get(k) != v for k, v in body.items()):
                    raise PlaneError("Ambiguous create reconciliation found duplicate/conflicting canonical identity")
                if matches:
                    entry.update(outcome="RECONCILED", entity_id=matches[0]["id"])
                    return matches[0]
                if attempt < 5:
                    continue
                raise PlaneError("Create retries exhausted after 5 attempts; fresh inventory found no intended entity")
            entry["outcome"] = "REJECTED"
            raise PlaneError(f"Plane mutation failed: HTTP {status}; response body redacted")

    def _raw(self, kind):
        return self.reader._list(self.prefix + kind + "/")

    def _audit(self):
        audit = self.reader.audit()
        if audit["work_items"]:
            raise PlaneError("CTRL-PM-008 expected zero work items; stop without importing")
        return audit

    def _check_rename(self, states):
        old = [s for s in states if s.get("name") == OLD_STATE]
        new = [s for s in states if s.get("name") == NEW_STATE]
        if len(old) == 1 and not new and old[0]["id"] == self.state_id:
            return old[0], False
        # Safe resume: only the exact previously approved state ID may already be corrected.
        if not old and len(new) == 1 and new[0]["id"] == self.state_id:
            return new[0], True
        raise PlaneError("State rename preconditions failed; no further mutations permitted")

    def _check_family(self, audit, kind):
        plan = bootstrap_plan(self.project, audit)
        if plan["conflicts"]:
            raise PlaneError("Structural discovery conflict; no further mutations permitted")
        ops = [o for o in plan["operations"] if o["kind"] == kind and o["identity"] != "BLOCKED"]
        expected_names = {o["identity"] for o in ops} | ({"BLOCKED"} if kind == "labels" else set())
        if any(r.get("name") not in expected_names for r in audit[kind]):
            raise PlaneError("Unexpected structural entity found; no further mutations permitted")
        if any(o["action"] not in {"create", "unchanged"} for o in ops):
            raise PlaneError("Existing structure differs from approved metadata; update not authorized")
        if kind == "cycles" and any(r.get("start_date") is not None or r.get("end_date") is not None for r in audit["cycles"]):
            raise PlaneError("Existing cycle contains calendar dates; date mutations not authorized")
        return ops

    def apply(self):
        try:
            before = self._audit()
            self.report["before"] = before
            blocked = [r for r in self._raw("labels") if r.get("name") == "BLOCKED"]
            if len(blocked) != 1:
                raise PlaneError("Expected exactly one existing BLOCKED label")
            states_before = self._raw("states")
            self.report["workflow_before"] = states_before
            self.report["blocked_before"] = blocked
            state, renamed = self._check_rename(states_before)
            # Check every structure before the first write, then recheck at each family.
            projected = {**before, "states": [{**s, "name": NEW_STATE} if s["id"] == self.state_id else s for s in before["states"]]}
            for kind in ["modules", "cycles", "labels"]:
                ops = self._check_family(projected, kind)
                self.allowed_creates.update({(kind + "/", o["identity"]): o["desired"] for o in ops})
            self.report["state_rename"] = {"before": state, "already_corrected": renamed}
            if not renamed:
                returned = self._write("PATCH", f"states/{self.state_id}/", {"name": NEW_STATE}, NEW_STATE)
                if returned["id"] != self.state_id:
                    raise PlaneError("State PATCH returned a different ID")
            states_after = self._raw("states")
            corrected, complete = self._check_rename(states_after)
            if not complete or _semantic(corrected) != {**_semantic(state), "name": NEW_STATE}:
                raise PlaneError("State rename changed unrelated fields or did not persist")
            untouched_before = {s["id"]: _semantic(s) for s in states_before if s["id"] != self.state_id}
            untouched_after = {s["id"]: _semantic(s) for s in states_after if s["id"] != self.state_id}
            if untouched_before != untouched_after:
                raise PlaneError("Other workflow states changed unexpectedly")
            self.report["state_rename"]["after"] = corrected
            if not renamed:
                self.report["mutations"][-1]["outcome"] = "VERIFIED"
            for kind in ["modules", "cycles", "labels"]:
                audit = self._audit()  # Fresh identity and full inventory for every mutation family.
                for op in self._check_family(audit, kind):
                    if op["action"] == "unchanged":
                        continue
                    # Re-read exact family before every individual create as well.
                    current = self._raw(kind)
                    matches = [r for r in current if r.get("name") == op["identity"]]
                    if matches:
                        if len(matches) != 1 or any(matches[0].get(k) != v for k, v in op["desired"].items()):
                            raise PlaneError("Structure changed concurrently; stop before create")
                        continue
                    returned = self._write("POST", kind + "/", op["desired"], op["identity"])
                    fresh = [r for r in self._raw(kind) if r.get("name") == op["identity"]]
                    if len(fresh) != 1 or fresh[0]["id"] != returned["id"] or any(fresh[0].get(k) != v for k, v in op["desired"].items()):
                        raise PlaneError("Created structure did not verify exactly")
                    if kind == "cycles" and (fresh[0].get("start_date") is not None or fresh[0].get("end_date") is not None):
                        raise PlaneError("API invented cycle dates; stop without date correction")
                    self.report["mutations"][-1]["outcome"] = "VERIFIED"
            after = self._audit()
            self.report["after"] = after
            workflow_after = self._raw("states")
            self.report["workflow_after"] = workflow_after
            expected_states = {s["id"]: {**_semantic(s), "name": NEW_STATE} if s["id"] == self.state_id
                               else _semantic(s) for s in states_before}
            if {s["id"]: _semantic(s) for s in workflow_after} != expected_states:
                raise PlaneError("Workflow semantics changed during structural bootstrap")
            if [r for r in self._raw("labels") if r.get("name") == "BLOCKED"] != blocked:
                raise PlaneError("BLOCKED label changed unexpectedly")
            self.report["blocked_after"] = blocked
            for kind in ["modules", "cycles", "labels"]:
                self._check_family(after, kind)
            plan = bootstrap_plan(self.project, after)
            structures = [o for o in plan["operations"] if o["kind"] != "work_items"]
            if any(o["action"] != "unchanged" for o in structures) or plan["conflicts"]:
                raise PlaneError("Post-apply structural dry-run is not unchanged and conflict-free")
            self.report["structural_idempotency"] = {"creates": 0, "required_updates": 0, "conflicts": 0,
                                                    "unchanged": len(structures)}
            self.report["mutation_counts"] = dict(Counter(m["method"] for m in self.report["mutations"]))
            self.report["result"] = "PASS"
            self.report["reads"] = self.reader.reads.copy()
            self.report["request_events"] = self.stream.events.copy()
            return self.report
        except PlaneError as exc:
            self.report["error"] = str(exc)
            self.report["reads"] = self.reader.reads.copy()
            self.report["request_events"] = self.stream.events.copy()
            raise BootstrapFailure(str(exc), self.report) from None
