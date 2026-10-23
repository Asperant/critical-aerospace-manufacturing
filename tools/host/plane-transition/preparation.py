"""CTRL-HOST-006: bounded, reproducible governance preparation; no product evidence.

Only workstreams without HARD START gates, with explicit later-stage evidence,
can be fully derived. Research and unknown consumer requirements fail closed.
Everything else retains UNKNOWN and requires actual consumer/readiness decisions.
"""

import hashlib
import json
import re

SCHEMA = "cap-preparation-v1"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def path_for(wp):
    if not re.fullmatch(r"WP-[A-Z0-9]+-[0-9]{3}", wp):
        raise ValueError("INVALID_WP")
    return f"evidence/{wp}/AUTO_PREPARATION.md"


def inputs(context, policy):
    return {"context": context, "sources": policy["source_manifest"], "engine": SCHEMA}


def derive(context, policy, source_sha):
    """Facts, planned acceptance and bounded workstream declaration, never execution."""
    if not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("INVALID_SOURCE_SHA")
    w = context["work_package"]
    wp = w["id"]
    refs = [
        "repo:" + p
        for p in (
            "docs/04_Work_Breakdown_Structure.md",
            "docs/03_Requirements_Traceability_Matrix.md",
            "docs/05_Dependency_Graph.md",
        )
    ]
    checks = {}

    def add(identity, condition, reason, evidence=None, result="PASS"):
        checks[identity] = {
            "result": result if condition else "UNKNOWN",
            "reason": reason,
            "evidence_refs": evidence or refs,
        }

    edges = context["dependency_edges"]
    # Stage is canonical: INTEGRATION/MILESTONE_EXIT/FREEZE are never START gates.
    start_clear = bool(w.get("inputs_required_contracts")) and all(
        edge["semantics"]["blocking_stage"]
        in {"INTEGRATION", "MILESTONE_EXIT", "FREEZE"}
        and bool(edge.get("precise_requirement") or edge.get("unblock_evidence"))
        for edge in edges
    )
    nonresearch = w.get("scope_class") in {"F0", "F1"} and all(
        x.get("scope_class") != "R1" for x in context["requirements"]
    )
    metadata = bool(
        w.get("purpose") and context.get("milestone_id") and w.get("readiness_refs")
    )
    routing = bool(w.get("primary_owner") and w.get("supporting_reviewers"))
    workstream = bool(
        w.get("major_tasks")
        and w.get("deliverables")
        and w.get("verification_expectations")
    )
    add(
        "DOR-TASK-01",
        metadata,
        "Canonical outcome/milestone/readiness node copied verbatim; planning only.",
    )
    add(
        "DOR-TASK-02",
        bool(w.get("requirement_refs") and context["requirements"]),
        "Current canonical requirements and wording retained.",
    )
    add(
        "DOR-TASK-03",
        routing,
        "Canonical owner/supporting reviewer; exact advisory evidence routing checked at current SHA.",
        ["repo:.github/CODEOWNERS"],
    )
    add(
        "DOR-TASK-04",
        start_clear,
        "No canonical HARD START edge. Later-stage exact consumer/evidence obligations are declared and deferred to their actual gates; no readiness asserted.",
    )
    add(
        "DOR-TASK-05",
        start_clear,
        "Canonical graph has no START contract gate. Start slice stays below integration/milestone gates; consumed contract evidence must exist before crossing those gates.",
    )
    add(
        "DOR-TASK-06",
        workstream,
        "Canonical deliverables/tasks and verification families define planned acceptance below; no tests executed.",
    )
    add(
        "DOR-TASK-07",
        workstream,
        "Canonical verification families copied; initial isolated component work, integration evidence remains pending.",
    )
    add(
        "DOR-TASK-08",
        True,
        "Conservative product risk estimate CR-4; reassess actual implementation PR. Preparation is governance only; CHG-018 zero approvals.",
        ["repo:09_change/CHG-018.yaml"],
    )
    add(
        "DOR-TASK-09",
        start_clear and bool(w.get("architecture_refs")),
        "Start only canonical first task within listed architecture; no new authority/technology choice authorized. Stop on contradiction.",
        ["repo:docs/02_System_Architecture_Specification.md"],
    )
    add(
        "DOR-TASK-10",
        workstream,
        "Treat WP as workstream; start with first canonical major task, then remaining listed tasks. Re-slice before expansion; no whole-WP duration claim.",
        ["repo:" + path_for(wp)],
    )
    add(
        "DOR-TASK-11",
        start_clear,
        "No canonical START prerequisite; live BLOCKED and current-work exclusion independently rechecked. Exact later-stage obligations remain unresolved, never certified.",
    )
    add(
        "DOR-TASK-12",
        nonresearch,
        "Canonical scope is non-R1; no research partition/FINAL access authorized.",
        result="N/A",
    )
    mapping = {
        "01": "02",
        "02": "01",
        "03": "04",
        "04": "04",
        "05": "05",
        "06": "07",
        "07": "03",
        "08": "12",
    }
    for suffix, task in mapping.items():
        checks["DOR-WP-" + suffix] = dict(checks["DOR-TASK-" + task])
    return {
        "schema_version": SCHEMA,
        "wp_id": wp,
        "source_sha": source_sha,
        "input_digest": digest(inputs(context, policy)),
        "accountable_owner": w["primary_owner"]["canonical_name"],
        "supporting_reviewers": w["supporting_reviewers"],
        "outcome": w["purpose"],
        "target": [context["milestone_id"], w["readiness_refs"]],
        "requirements": [
            {"id": x["id"], "statement": x["statement"]}
            for x in context["requirements"]
        ],
        "architecture_refs": w["architecture_refs"],
        "deferred_dependencies": [
            {
                "dependency_id": edge["id"],
                "semantics": edge["semantics"],
                "consumer_requirement": edge.get("precise_requirement")
                or edge.get("unblock_evidence"),
                "readiness": "NOT_CERTIFIED",
            }
            for edge in edges
        ],
        "start_slice": (w["major_tasks"] or [None])[0],
        "remaining_workstream": w["major_tasks"][1:],
        "planned_acceptance": w["deliverables"],
        "planned_verification": w["verification_expectations"],
        "product_implementation": "NOT_YET_EXECUTED",
        "readiness_artifacts": "NOT_PRODUCED",
        "test_results": "NOT_EXECUTED",
        "checks": checks,
    }


def encode(plan):
    return json.dumps(plan, sort_keys=True, ensure_ascii=True, indent=2) + "\n"


def classify(candidate, plan=None):
    if candidate.get("status") == "UNAVAILABLE":
        return "UNAVAILABLE"
    if candidate.get("hard_start_blockers"):
        return "WAITING_DEP"
    if candidate.get("status") == "PREPARED":
        return "VERIFIED_PREPARED"
    if candidate.get("status") == "BLOCKED":
        return "REAL_WORK_REQUIRED"
    if plan is None:
        return "UNAVAILABLE"
    deficits = candidate.get("deficits", [])
    if any(d.get("canonical_id") not in plan["checks"] for d in deficits):
        return "REAL_WORK_REQUIRED"
    ids = [d["canonical_id"] for d in deficits] or list(plan["checks"])
    if any(plan["checks"][key]["result"] == "UNKNOWN" for key in ids):
        return "REAL_WORK_REQUIRED"
    return "AUTO_PREPARABLE"


def routing_line(context, github):
    w = context["work_package"]
    names = [w["primary_owner"]["canonical_name"]] + [
        x["canonical_name"] for x in w["supporting_reviewers"]
    ]
    return (
        "/evidence/"
        + w["id"]
        + "/ "
        + " ".join("@" + github[n] for n in dict.fromkeys(names))
    )


def verify_remote_sources(t, gh, sha, policy):
    """A current main SHA alone cannot prove a pinned policy is still canonical."""
    expected = policy.get("source_git_blobs", {})
    t.need(
        bool(expected) and set(expected) == set(policy["source_manifest"]),
        "REMOTE_CANONICAL_SOURCE_UNAVAILABLE_POLICY_REFRESH_REQUIRED",
    )
    tree = gh._get(f"{t.REPO}/git/trees/{sha}?recursive=1")
    t.need(
        tree.get("truncated") is False,
        "REMOTE_CANONICAL_SOURCE_UNAVAILABLE_TREE_INCOMPLETE",
    )
    blobs = {
        row["path"]: row.get("sha")
        for row in tree.get("tree", [])
        if row.get("type") == "blob"
    }
    t.need(
        all(
            re.fullmatch(r"[a-f0-9]{40}", value) and blobs.get(path) == value
            for path, value in expected.items()
        ),
        "REMOTE_CANONICAL_SOURCE_UNAVAILABLE_POLICY_REFRESH_REQUIRED",
    )


def verified_record(t, gh, wp, sha, policy):
    """Recompute every field from pinned policy; never trust supplied PASS or SHA.

    CHG-021 permits this *mechanically derived* START assessment, without pretending
    to be an owner-authored comment. Semantic/DoD assessments keep attribution rules.
    """
    t.need(policy.get("preparation_schema") == SCHEMA, "PREPARATION_POLICY_UNAVAILABLE")
    verify_remote_sources(t, gh, sha, policy)
    context = policy["contexts"][wp]
    raw = gh.evidence_text(path_for(wp), sha)
    data = json.loads(raw)
    expected = derive(context, policy, data["source_sha"])
    t.need(data == expected, "PREPARATION_INPUT_CHANGED_OR_INVALID")
    t.need(
        all(x["result"] in {"PASS", "N/A"} for x in expected["checks"].values()),
        "PREPARATION_REAL_WORK_REQUIRED",
    )
    comparison = gh._get(f"{t.REPO}/compare/{data['source_sha']}...{sha}")
    t.need(
        comparison.get("status") in {"ahead", "identical"},
        "PREPARATION_SOURCE_NOT_ANCESTOR",
    )
    import base64

    route = gh._get(f"{t.REPO}/contents/.github/CODEOWNERS?ref={sha}")
    text = base64.b64decode(route["content"]).decode()
    names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
    # Exact final rule: later wildcard routing cannot silently shadow it.
    import fnmatch

    line = routing_line(context, names)
    lines = text.splitlines()
    t.need(line in lines, "PREPARATION_ROUTING_CHANGED")
    last = len(lines) - 1 - lines[::-1].index(line)
    sample = "evidence/" + wp + "/AUTO_PREPARATION.md"
    for later in lines[last + 1 :]:
        parts = later.split()
        if not parts or parts[0].startswith("#"):
            continue
        pattern = parts[0].lstrip("/")
        t.need(
            not fnmatch.fnmatch(
                sample, pattern + ("*" if pattern.endswith("/") else "")
            ),
            "PREPARATION_ROUTING_SHADOWED",
        )
    return {
        "wp_id": wp,
        "head_sha": sha,
        "checks": expected["checks"],
        "reason": "CHG-021 freshly recomputed canonical START preparation",
        "_derived": True,
    }
