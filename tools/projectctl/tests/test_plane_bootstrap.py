from copy import deepcopy
import json

import httpx
import pytest

from projectctl.plane import PlaneConfig, PlaneError
from projectctl.plane_bootstrap import BootstrapFailure, StructureBootstrap
from projectctl.plane_plan import STATES
from projectctl.project import load_project

PROJECT_ID = "beb6dbea-4931-4ce9-b761-a4957c4b33be"
STATE_ID = "99a0cc57-ec65-4c3d-8db4-694ce31c77fa"
SECRET = "test-bootstrap-secret"


class FakePlane:
    def __init__(self):
        self.states = [{"id": STATE_ID if s == "IN_REVIEW" else s, "name": "IN_REVİEW" if s == "IN_REVIEW" else s,
                        "color": "#f59e0b", "sequence": 70000, "group": "started", "slug": s.lower(),
                        "default": False, "description": "preserve this"} for s in STATES]
        self.rows = {"states": self.states, "labels": [{"id": "blocked", "name": "BLOCKED", "color": "#aabbcc"}],
                     "modules": [], "cycles": [], "issues": []}
        self.writes = []
        self.fail_name = None
        self.inject_dates = False
        self.change_state = False

    def handle(self, req):
        assert req.url.path.startswith("/api/v1/")
        assert req.headers["X-API-Key"] == SECRET
        path = req.url.path
        project = {"id": PROJECT_ID, "name": "Graduation Project", "identifier": "CAP", "workspace": "workspace"}
        if req.method == "GET":
            if path.endswith("users/me/"):
                return httpx.Response(200, json={"id": "user"})
            if path.endswith("workspaces/test/"):
                return httpx.Response(401)
            if path.endswith("projects/"):
                return httpx.Response(200, json=[project])
            if path.endswith(f"projects/{PROJECT_ID}/"):
                return httpx.Response(200, json=project)
            if path.endswith("members/"):
                return httpx.Response(200, json=[])
            kind = path.rstrip("/").split("/")[-1]
            return httpx.Response(200, json=deepcopy(self.rows[kind]))
        body = json.loads(req.content)
        self.writes.append((req.method, path, body))
        if body["name"] == self.fail_name:
            return httpx.Response(400, text=SECRET)
        if req.method == "PATCH":
            assert path.endswith(f"states/{STATE_ID}/") and body == {"name": "IN_REVIEW"}
            state = next(s for s in self.states if s["id"] == STATE_ID)
            state.update(body)
            if self.change_state:
                state["color"] = "changed"
            return httpx.Response(200, json=deepcopy(state))
        assert req.method == "POST"
        kind = path.rstrip("/").split("/")[-1]
        assert kind in {"modules", "cycles", "labels"}
        assert set(body) <= {"name", "description"}
        entity = {"id": f"{kind}-{body['name']}", **body}
        if kind == "cycles":
            entity.update(start_date="invented" if self.inject_dates else None, end_date=None)
        self.rows[kind].append(entity)
        return httpx.Response(201, json=deepcopy(entity))


@pytest.fixture
def project(root):
    return load_project(root)


def bootstrap(project, fake, approved=True):
    return StructureBootstrap(PlaneConfig("http://plane.test", SECRET, "test", PROJECT_ID), project,
                              STATE_ID, approved=approved, transport=httpx.MockTransport(fake.handle))


def test_exact_approved_scope_preservation_and_idempotent_resume(project):
    fake = FakePlane()
    states = deepcopy(fake.states)
    blocked = deepcopy(fake.rows["labels"][0])
    with bootstrap(project, fake) as runner:
        report = runner.apply()
    assert report["result"] == "PASS"
    assert report["mutation_counts"] == {"PATCH": 1, "POST": 51}
    assert all(m["outcome"] == "VERIFIED" and m["entity_id"] for m in report["mutations"])
    assert len(fake.rows["modules"]) == 29 and len(fake.rows["cycles"]) == 13 and len(fake.rows["labels"]) == 10
    assert fake.rows["labels"][0] == blocked and fake.rows["issues"] == []
    for before, after in zip(states, fake.states):
        assert after == {**before, "name": "IN_REVIEW"} if before["id"] == STATE_ID else after == before
    assert all(c["start_date"] is None and c["end_date"] is None for c in fake.rows["cycles"])
    assert report["structural_idempotency"] == {"creates": 0, "required_updates": 0, "conflicts": 0, "unchanged": 52}
    assert SECRET not in json.dumps(report)
    with bootstrap(project, fake) as runner:
        second = runner.apply()
    assert second["result"] == "PASS" and second["mutations"] == []
    assert len(fake.writes) == 52


@pytest.mark.parametrize("failure", ["duplicate_old", "correct_exists", "wrong_id", "missing_old", "blocked_missing", "duplicate_module", "dated_cycle"])
def test_false_preconditions_stop_before_any_mutation(project, failure):
    fake = FakePlane()
    state = next(s for s in fake.states if s["id"] == STATE_ID)
    if failure == "duplicate_old":
        fake.states.append({**state, "id": "other"})
    elif failure == "correct_exists":
        fake.states.append({**state, "id": "other", "name": "IN_REVIEW"})
    elif failure == "wrong_id":
        state["id"] = "wrong"
    elif failure == "missing_old":
        state["name"] = "Unexpected"
    elif failure == "blocked_missing":
        fake.rows["labels"] = []
    elif failure == "duplicate_module":
        fake.rows["modules"] = [{"id": "a", "name": "WP-CORE"}, {"id": "b", "name": "WP-CORE"}]
    elif failure == "dated_cycle":
        fake.rows["cycles"] = [{"id": "s", "name": "S1", "start_date": "2026-01-01"}]
    with bootstrap(project, fake) as runner:
        with pytest.raises(BootstrapFailure) as error:
            runner.apply()
    assert fake.writes == [] and error.value.report["result"] == "INCOMPLETE"


def test_partial_failure_stops_without_rollback_and_resume_creates_only_missing(project):
    fake = FakePlane()
    fake.fail_name = "WP-BENCH"
    with bootstrap(project, fake) as runner:
        with pytest.raises(BootstrapFailure) as error:
            runner.apply()
    report = error.value.report
    assert len(fake.rows["modules"]) == 2 and len(fake.rows["cycles"]) == 0
    assert report["mutations"][-1]["outcome"] == "REJECTED"
    assert SECRET not in json.dumps(report)
    assert all(method in {"PATCH", "POST"} for method, _, _ in fake.writes)
    fake.fail_name = None
    with bootstrap(project, fake) as runner:
        resumed = runner.apply()
    assert resumed["mutation_counts"] == {"POST": 49} and resumed["result"] == "PASS"


@pytest.mark.parametrize("change", ["date", "state"])
def test_api_side_effects_stop_without_repairs(project, change):
    fake = FakePlane()
    fake.inject_dates = change == "date"
    fake.change_state = change == "state"
    with bootstrap(project, fake) as runner:
        with pytest.raises(BootstrapFailure):
            runner.apply()
    assert len(fake.rows["cycles"]) == (1 if change == "date" else 0)
    assert len(fake.writes) == (31 if change == "date" else 1)


def test_explicit_approval_and_write_allowlist(project):
    fake = FakePlane()
    with pytest.raises(PlaneError, match="approval"):
        bootstrap(project, fake, approved=False)
    with bootstrap(project, fake) as runner:
        for method, suffix, body in [("POST", "issues/", {"name": "WP-CORE-001"}),
                                     ("DELETE", "modules/id/", {}),
                                     ("PATCH", f"states/{STATE_ID}/", {"name": "IN_REVIEW", "group": "completed"}),
                                     ("POST", "cycles/", {"name": "S1", "start_date": "2026-01-01"}),
                                     ("POST", "labels/", {"name": "BLOCKED"})]:
            with pytest.raises(PlaneError, match="scope"):
                runner._write(method, suffix, body, body.get("name"))
    assert fake.writes == []


@pytest.mark.parametrize("failure", ["timeout", "invalid_json", "429_after_commit", "500_after_commit"])
def test_ambiguous_create_is_reconciled_without_duplicate_post(project, failure):
    fake=FakePlane()
    original=fake.handle
    injected=False
    def handler(req):
        nonlocal injected
        result=original(req)
        if req.method=="POST" and not injected:
            injected=True
            if failure=="timeout": raise httpx.ReadTimeout("redacted test failure",request=req)
            if failure=="invalid_json": return httpx.Response(201,text="invalid")
            return httpx.Response(429 if failure=="429_after_commit" else 500,headers={"Retry-After":"5"})
        return result
    fake.handle=handler
    with bootstrap(project,fake) as runner:
        report=runner.apply()
    assert report["result"]=="PASS"
    assert len(fake.writes)==52 and len(fake.rows["modules"])==29
    first=next(m for m in report["mutations"] if m["method"]=="POST")
    assert len(first["attempts"])==1 and first["entity_id"]==fake.rows["modules"][0]["id"]


def test_429_create_retries_only_after_empty_inventory_and_required_wait(project):
    import projectctl.plane_transport as transport
    fake=FakePlane(); original=fake.handle
    failed=False; timing=[]
    def handler(req):
        nonlocal failed
        if req.method=="POST" and json.loads(req.content)["name"]=="WP-AI":
            timing.append(transport.monotonic())
            if not failed:
                failed=True
                return httpx.Response(429,headers={"Retry-After":"10"})
        return original(req)
    fake.handle=handler
    with bootstrap(project,fake) as runner:
        report=runner.apply()
    assert report["result"]=="PASS" and len(fake.rows["modules"])==29
    assert len(timing)==2 and timing[1]-timing[0]>=10
    assert len(next(m for m in report["mutations"] if m["identity"]=="WP-AI")["attempts"])==2


def test_exhausted_create_stops_with_fresh_inventory_and_no_other_creates(project):
    fake=FakePlane(); original=fake.handle; posts=[]
    def handler(req):
        if req.method=="POST":
            posts.append(req)
            return httpx.Response(429)
        return original(req)
    fake.handle=handler
    with bootstrap(project,fake) as runner:
        with pytest.raises(BootstrapFailure,match="5 attempts"):
            runner.apply()
    assert len(posts)==5 and not fake.rows["modules"] and not fake.rows["cycles"]


def test_duplicate_during_ambiguous_create_stops_without_retry(project):
    fake=FakePlane(); original=fake.handle
    def handler(req):
        result=original(req)
        if req.method=="POST":
            fake.rows["modules"].append({**fake.rows["modules"][-1],"id":"duplicate"})
            return httpx.Response(500)
        return result
    fake.handle=handler
    with bootstrap(project,fake) as runner:
        with pytest.raises(BootstrapFailure,match="duplicate/conflicting"):
            runner.apply()
    assert len(fake.writes)==2
