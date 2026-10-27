import html
import json
from copy import deepcopy

import httpx
import pytest
from projectctl.plane import PlaneConfig, PlaneError
from projectctl.plane_import import (
    MILESTONES,
    UNSCHEDULED,
    ImportFailure,
    WPImport,
    canonical_metadata,
    check_issue,
    expected_projection,
)
from projectctl.plane_plan import STATES, bootstrap_plan
from projectctl.project import load_project

PROJECT = "beb6dbea-4931-4ce9-b761-a4957c4b33be"
SECRET = "mock-import-secret"


@pytest.fixture(scope="module")
def project():
    from pathlib import Path

    return load_project(Path(__file__).resolve().parents[3])


class FakePlane:
    def __init__(self, project):
        self.audit = {
            "schema_version": "plane-v1-audit-v1",
            "api_version": "v1",
            "mutation_enabled": False,
            "workspace": {"id": "workspace", "slug": "test"},
            "project": {
                "id": PROJECT,
                "name": "Graduation Project",
                "identifier": "CAP",
                "workspace": "workspace",
            },
            "states": [{"id": s, "name": s} for s in STATES],
            "labels": [{"id": "blocked", "name": "BLOCKED"}],
            "modules": [],
            "cycles": [],
            "work_items": [],
            "project_members": [
                {"id": "asrin", "first_name": "Asrın", "last_name": "Dündar"},
                {"id": "batuhan", "first_name": "Batuhan", "last_name": "Kaya"},
                {"id": "selman", "first_name": "Selman", "last_name": "Özdemir"},
                {"id": "yavuz", "first_name": "Yavuz", "last_name": "Gümüş"},
            ],
            "workspace_members": [],
        }
        for op in bootstrap_plan(project, self.audit)["operations"]:
            if op["kind"] != "work_items" and op["action"] == "create":
                self.audit[op["kind"]].append({"id": op["identity"], **op["desired"]})
        self.memberships = {"modules": {}, "cycles": {}}
        self.default = None
        self.writes = []
        self.failure = None
        self.failed = False
        self.corrupt = None
        self.links = False

    def handle(self, req):
        assert (
            req.url.path.startswith("/api/v1/") and req.headers["X-API-Key"] == SECRET
        )
        path = req.url.path.rstrip("/").split("/")
        tail = path[-1]
        if req.method == "GET":
            if req.url.path.endswith("users/me/"):
                data = {"id": "asrin"}
            elif req.url.path.endswith("workspaces/test/"):
                return httpx.Response(401)
            elif tail == "projects":
                data = [self.audit["project"]]
            elif tail == PROJECT:
                data = {**self.audit["project"], "default_assignee": self.default}
            elif tail == "members":
                data = self.audit["project_members"]
            elif tail == "relations":
                data = {
                    "blocking": ["unexpected"] if self.links else [],
                    "blocked_by": [],
                }
            elif tail in {"module-issues", "cycle-issues"}:
                family = "modules" if tail == "module-issues" else "cycles"
                data = [
                    i
                    for i in self.audit["work_items"]
                    if path[-2] in self.memberships[family].get(i["id"], [])
                ]
            elif path[-2] == "issues":
                data = next(i for i in self.audit["work_items"] if i["id"] == tail)
            else:
                data = self.audit["work_items" if tail == "issues" else tail]
            return httpx.Response(200, json=deepcopy(data))
        if req.method == "PATCH":
            assert path[-2] == "issues"
            body = json.loads(req.content)
            self.writes.append(("issue-patch", body))
            item = next(i for i in self.audit["work_items"] if i["id"] == tail)
            item.update(deepcopy(body))
            return httpx.Response(200, json=deepcopy(item))
        if req.method == "DELETE":
            assert tail == path[-1] and path[-2] in {"module-issues", "cycle-issues"}
            family = "modules" if path[-2] == "module-issues" else "cycles"
            entity_id, issue_id = path[-3], path[-1]
            self.writes.append(
                (
                    "relationship-delete",
                    {"family": family, "entity": entity_id, "issue": issue_id},
                )
            )
            current = self.memberships[family].get(issue_id, [])
            self.memberships[family][issue_id] = [
                value for value in current if value != entity_id
            ]
            return httpx.Response(204)
        assert req.method == "POST" and tail in {
            "issues",
            "module-issues",
            "cycle-issues",
        }
        body = json.loads(req.content)
        self.writes.append((tail, body))
        fail = self.failure and not self.failed and self.failure[0] == tail
        if fail and self.failure[1] == "429_absent":
            self.failed = True
            return httpx.Response(429, headers={"Retry-After": "10"})
        if tail == "issues":
            data = {
                "id": "issue-" + body["external_id"],
                **deepcopy(body),
                "parent": None,
            }
            # Server may wrap sibling HTML roots and normalize escaped text.
            data["description_html"] = (
                "<div>" + data["description_html"].replace("&#x27;", "'") + "</div>"
            )
            if self.corrupt == "labels":
                data["labels"] = []
            elif self.corrupt == "state":
                data["state"] = "READY"
            elif self.corrupt == "metadata":
                data["description_html"] = "<p>lost metadata</p>"
            self.audit["work_items"].append(data)
        else:
            family = "modules" if tail == "module-issues" else "cycles"
            issue_id = body["issues"][0]
            assert not self.memberships[family].get(
                issue_id
            ), "must skip existing relationships"
            self.memberships[family][issue_id] = [path[-2]]
            data = {"id": "association"}
        if fail:
            self.failed = True
            if self.failure[1] == "timeout":
                raise httpx.ReadTimeout(SECRET, request=req)
            if self.failure[1] == "bad_json":
                return httpx.Response(201, text=SECRET)
            return httpx.Response(500, headers={"Retry-After": "5"})
        return httpx.Response(201 if tail == "issues" else 200, json=deepcopy(data))


def runner(project, fake, approved=True):
    return WPImport(
        PlaneConfig("http://plane.test", SECRET, "test", PROJECT),
        project,
        approved=approved,
        transport=httpx.MockTransport(fake.handle),
    )


def test_exact_full_import_pilot_scope_html_and_live_noop(project):
    fake = FakePlane(project)
    before = deepcopy(fake.audit)
    checkpoints = []
    with runner(project, fake) as run:
        report = run.run(
            checkpoint=lambda r: checkpoints.append(
                (len(fake.writes), deepcopy(r["pilot_expected"]))
            )
        )
    assert checkpoints[0][0] == 0
    assert report["projection"]["pilot_wp_id"] == "WP-AI-007"
    assert fake.writes[0][1]["external_id"] == "WP-AI-007"
    assert report["pilot_result"]["result"] == "PASS" and report["result"] == "PASS"
    assert len(fake.writes) == 535
    assert CounterWrites(fake) == {
        "issues": 180,
        "module-issues": 180,
        "cycle-issues": 175,
    }
    assert len(fake.audit["work_items"]) == 180
    for item in fake.audit["work_items"]:
        metadata = canonical_metadata(item["description_html"])
        assert item["name"].startswith("[" + item["external_id"] + "] ")
        assert (
            item["state"] == "BACKLOG"
            and metadata["PrimaryOwner"] == metadata["canonical_owner"]
        )
        assert item["assignees"] == [
            {
                "Asrın Dündar": "asrin",
                "Batuhan Kaya": "batuhan",
                "Selman Özdemir": "selman",
                "Yavuz Gümüş": "yavuz",
            }[metadata["canonical_owner"]]
        ]
        assert len(fake.memberships["modules"][item["id"]]) == 1
        if item["external_id"] in UNSCHEDULED:
            assert not item["labels"] and not fake.memberships["cycles"].get(item["id"])
        else:
            assert fake.memberships["cycles"][item["id"]] == [metadata["cycle_ids"][0]]
            assert item["labels"] == ["MS:" + metadata["milestone"]]
            assert metadata["canonical_sprint_window"]
    assert report["post_import"]["summary"]["milestone_distribution"] == MILESTONES
    assert report["before"]["memberships"] == {"modules": {}, "cycles": {}}
    for resource in ("modules", "cycles", "labels", "states"):
        assert fake.audit[resource] == before[resource]
    with runner(project, fake) as run:
        second = run.run()
    assert second["result"] == "PASS" and second["mutations"] == []
    assert (
        second["preview"]["http_mutation_requests"] == 0
        and second["preview"]["unchanged"] == 180
    )
    assert SECRET not in json.dumps(report) and SECRET not in json.dumps(second)


def CounterWrites(fake):
    from collections import Counter

    return dict(Counter(kind for kind, _ in fake.writes))


def test_existing_relationship_drift_is_repaired_without_state_reset(project):
    fake = FakePlane(project)
    projection = expected_projection(project, fake.audit)
    first = projection["projections"][0]
    second = projection["projections"][1]
    fake.audit["work_items"] = [
        {"id": "first", **first["create_body"]},
        {"id": "second", **second["create_body"], "state": "READY"},
    ]
    fake.memberships["modules"] = {
        "first": [first["module_id"]],
        "second": [second["module_id"]],
    }
    fake.memberships["cycles"] = {
        "first": [first["cycle_id"]],
        "second": ["stale-cycle"],
    }
    # The normal audit cannot expose a noncanonical relation entity; use a real cycle
    # that is wrong for this issue, as the live Plane inventory does.
    wrong_cycle = next(
        e["id"] for e in fake.audit["cycles"] if e["id"] != second["cycle_id"]
    )
    fake.memberships["cycles"]["second"] = [wrong_cycle]
    with runner(project, fake) as run:
        run.prepare()
        assert run.report["preview"]["conflicts"] == []
        op = next(
            o
            for o in run.report["preview"]["operations"]
            if o["wp_id"] == second["wp_id"]
        )
        assert op["relationship_repairs"]["cycles"]["remove"] == [wrong_cycle]
        run.apply_one(first["wp_id"])
        run.apply_one(second["wp_id"])
    item = next(i for i in fake.audit["work_items"] if i["id"] == "second")
    assert item["state"] == "READY"
    assert fake.memberships["cycles"]["second"] == [second["cycle_id"]]
    assert any(kind == "relationship-delete" for kind, _ in fake.writes)


@pytest.mark.parametrize("corrupt", ["labels", "state", "metadata"])
def test_pilot_failure_stops_bulk_without_repair(project, corrupt):
    fake = FakePlane(project)
    fake.corrupt = corrupt
    with runner(project, fake) as run, pytest.raises(ImportFailure) as error:
        run.run()
    assert len(fake.writes) == 1
    assert (
        error.value.report["human_gate"]
        == "BLOCKED_FOR_HUMAN: WP_IMPORT_CONTRACT_MISMATCH"
    )
    assert len(fake.audit["work_items"]) == 1


@pytest.mark.parametrize(
    "tail,mode",
    [
        ("issues", "timeout"),
        ("issues", "bad_json"),
        ("issues", "500"),
        ("module-issues", "timeout"),
        ("cycle-issues", "500"),
        ("module-issues", "429_absent"),
    ],
)
def test_ambiguous_writes_reconcile_without_duplicate_replay(project, tail, mode):
    fake = FakePlane(project)
    fake.failure = (tail, mode)
    with runner(project, fake) as run:
        report = run.run()
    assert report["result"] == "PASS" and len(fake.audit["work_items"]) == 180
    assert len(fake.writes) == (536 if mode == "429_absent" else 535)
    assert report["reconciliations"] and SECRET not in json.dumps(report)


def test_partial_resume_preserves_pilot_and_only_fills_absent_relations(project):
    fake = FakePlane(project)
    with runner(project, fake) as run:
        run.prepare()
        e = run.allowed[run.projection["pilot_wp_id"]]
        item = run._create(e)
    assert len(fake.writes) == 1
    with runner(project, fake) as run:
        report = run.run()
    assert report["result"] == "PASS" and len(fake.writes) == 535
    assert sum(b.get("external_id") == item["external_id"] for _, b in fake.writes) == 1


@pytest.mark.parametrize(
    "failure", ["default", "duplicate", "unknown", "blocked", "state"]
)
def test_unsafe_preconditions_fail_before_writes(project, failure):
    fake = FakePlane(project)
    projection = expected_projection(project, fake.audit)
    e = projection["projections"][0]
    item = {"id": "existing", **e["create_body"]}
    if failure == "default":
        fake.default = "asrin"
    elif failure == "duplicate":
        fake.audit["work_items"] = [item, {**item, "id": "other"}]
    elif failure == "unknown":
        fake.audit["work_items"] = [{"id": "unknown", "name": "FR-CORE-001"}]
    elif failure == "blocked":
        fake.audit["labels"] = [
            label for label in fake.audit["labels"] if label["name"] != "BLOCKED"
        ]
    else:
        fake.audit["states"][0]["name"] = "BLOCKED"
    with runner(project, fake) as run, pytest.raises(ImportFailure):
        run.run()
    assert fake.writes == []


def test_approval_and_exact_write_allowlist(project):
    fake = FakePlane(project)
    with pytest.raises(PlaneError, match="approval"):
        runner(project, fake, approved=False)
    with runner(project, fake) as run:
        run.prepare()
        e = run.allowed[run.projection["pilot_wp_id"]]
        for suffix, body in [
            ("labels/", {"name": "extra"}),
            ("members/", {}),
            ("issues/", {**e["create_body"], "state": "READY"}),
        ]:
            with pytest.raises(PlaneError, match="scope"):
                run._write(suffix, body, e["wp_id"], 1)
    assert not fake.writes


@pytest.mark.parametrize(
    "value",
    [
        '<pre>{"id":1,"id":2}</pre>',
        "<pre>{}</pre><pre>{}</pre>",
        '<pre>{"id":<b>1</b>}</pre>',
        "<pre>{}</pre><pre>",
        "<p>{}</p>",
    ],
)
def test_metadata_ambiguity_rejected(value):
    with pytest.raises(PlaneError):
        canonical_metadata(value)


def test_metadata_character_roundtrip():
    value = {"owner": "Asrın Dündar", "text": "<tag> & 'quoted' \"double\""}
    assert (
        canonical_metadata(
            "<div><pre>"
            + html.escape(json.dumps(value, ensure_ascii=False))
            + "</pre></div>"
        )
        == value
    )


@pytest.mark.parametrize(
    "wrapper",
    [
        "{}",
        "<pre>{}</pre>",
        "<pre><code>{}</code></pre>",
        '<div><pre data-id="editor"><code>{}</code></pre></div>',
    ],
)
def test_metadata_supported_representations_in_issue_check(project, wrapper):
    fake = FakePlane(project)
    expected = next(
        e
        for e in expected_projection(project, fake.audit)["projections"]
        if e["wp_id"] == "WP-VALID-001"
    )
    item = {"id": "existing", **deepcopy(expected["create_body"]), "parent": None}
    payload = json.dumps(expected["metadata"], ensure_ascii=False)
    item["description_html"] = wrapper.format(
        payload if wrapper == "{}" else html.escape(payload)
    )
    check_issue(item, expected)
    assert canonical_metadata(item["description_html"]) == expected["metadata"]


def test_code_wrapper_decodes_entities_once():
    value = {"owner": "Batuhan Kaya", "text": '<tag> &amp; & "quoted"'}
    payload = html.escape(json.dumps(value))
    assert canonical_metadata("<pre>\n<code>" + payload + "</code>\n</pre>") == value


@pytest.mark.parametrize(
    "value",
    [
        '<pre><code>{"id":}</code></pre>',
        '<pre><code>{"id":1,"id":2}</code></pre>',
        "<pre><code>[]</code></pre>",
        "<pre><code>{}</code></pre><pre>{}</pre>",
        "<pre><code>{}</pre>",
        "<pre><code>{}</code>",
        "<pre><code><code>{}</code></code></pre>",
        "<pre><code><span>{}</span></code></pre>",
        "<pre><code>{}</code><code>{}</code></pre>",
        "<pre>{}<code>{}</code></pre>",
        "<pre><code>{}</code>{}</pre>",
        "<pre><code>{}</b></code></pre>",
        "<pre><code>{<!-- hidden -->}</code></pre>",
        "<p><code>{}</code></p>",
        "<pre><code>{<!DOCTYPE hidden>}</code></pre>",
        "<pre><code>{<?hidden?>}</code></pre>",
        '{"id":}<b></b>',
        '{"id":1,"id":2}',
    ],
)
def test_metadata_code_wrapper_rejects_malformed_or_ambiguous_content(value):
    with pytest.raises(PlaneError):
        canonical_metadata(value)


def test_code_wrapper_does_not_hide_semantic_metadata_drift(project):
    fake = FakePlane(project)
    expected = next(
        e
        for e in expected_projection(project, fake.audit)["projections"]
        if e["wp_id"] == "WP-VALID-001"
    )
    changed = {**expected["metadata"], "canonical_owner": "Asrın Dündar"}
    item = {"id": "existing", **deepcopy(expected["create_body"]), "parent": None}
    item["description_html"] = (
        "<pre><code>" + html.escape(json.dumps(changed)) + "</code></pre>"
    )
    assert canonical_metadata(item["description_html"]) == changed
    with pytest.raises(PlaneError, match="reconciliation required: description_html"):
        check_issue(item, expected, allow_state_difference=True)


def test_second_run_never_resets_real_execution_state(project):
    fake = FakePlane(project)
    with runner(project, fake) as run:
        run.run()
    fake.audit["work_items"][0]["state"] = "IN_PROGRESS"
    count = len(fake.writes)
    with runner(project, fake) as run:
        report = run.run()
    assert report["result"] == "PASS"
    assert (
        len(fake.writes) == count
        and fake.audit["work_items"][0]["state"] == "IN_PROGRESS"
    )
    assert report["post_import"]["dry_run"]["preserved_state_differences"] == 1


def test_existing_static_drift_is_repaired_without_state_reset(project):
    fake = FakePlane(project)
    with runner(project, fake) as run:
        run.run()
    item = fake.audit["work_items"][0]
    item["description_html"] = "<p>stale static metadata</p>"
    item["assignees"] = ["wrong-owner"]
    item["state"] = "READY"
    count = len(fake.writes)
    with runner(project, fake) as run:
        report = run.run()
    patches = [body for kind, body in fake.writes[count:] if kind == "issue-patch"]
    assert len(patches) == 1
    assert set(patches[0]) == {"description_html", "assignees"}
    assert "state" not in patches[0]
    assert item["state"] == "READY"
    assert report["result"] == "PASS"
    assert report["post_import"]["dry_run"]["preserved_state_differences"] == 1
