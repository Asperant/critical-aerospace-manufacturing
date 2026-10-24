"""Offline check of the REAL generated policy against the reconcile code (no network, no host).

Usage (repository root, locked CI env): python lifecycle_offline_check.py <generated-policy.json>
Plane and GitHub are fixtures bound to the exact PR 52 values in the policy; nothing is
read from or written to Plane, GitHub or the host.
"""
import hashlib, importlib.util, json, pathlib, sys
from copy import deepcopy

REPO = pathlib.Path.cwd()
HOST = REPO / "tools/host"
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
t = load("t_offline", HOST / "plane-transition/transition.py")
t.q = load("q_offline", HOST / "plane-queue/queue.py")
r = load("r_offline", HOST / "plane-transition/reconcile.py"); r.t = t
ins = load("ins_offline", HOST / "plane-transition/install_auto_next.py")
policy = json.loads(pathlib.Path(sys.argv[1]).read_text())
out = {}
out["policy_digest"] = policy["policy_digest"]
out["reconcile_impl_sha256_in_policy"] = policy["implementation_sha256"]["reconcile"]
out["reconcile_py_sha256_actual"] = hashlib.sha256((HOST / "plane-transition/reconcile.py").read_bytes()).hexdigest()
out["transition_impl_matches"] = policy["implementation_sha256"]["transition"] == hashlib.sha256((HOST / "plane-transition/transition.py").read_bytes()).hexdigest()
out["manifest_has_policy_file"] = "project_control/lifecycle_reconciliation.yaml" in policy["source_manifest"]
out["manifest_has_chg031"] = "09_change/CHG-031.yaml" in policy["source_manifest"]
out["manifest_keeps_upstream_chg030"] = "09_change/CHG-030.yaml" in policy["source_manifest"]
block = r.validate_policy(policy["lifecycle_reconciliation"], policy["contexts"], t.q.PEOPLE)
(case,) = block["cases"]
out["case"] = {k: case[k] for k in ("case_id", "profile", "wp_id", "pr", "targets")}
out["grants"] = ins.reconcile_grants(policy)
# End-to-end with fixtures bound to the real case values.
WP, PROFILE = case["wp_id"], case["profile"]
class Plane:
    def __init__(self, state):
        names = dict(t.q.PEOPLE)
        self.item = {"id": "12345678-1234-1234-1234-123456789abc", "external_id": WP, "external_source": "projectctl",
            "name": f"[{WP}] Deterministic DES kernel", "description_html": json.dumps({"canonical_wp_id": WP, "canonical_owner": names[PROFILE][0]}),
            "state": state, "assignees": [names[PROFILE][1]], "labels": [], "priority": "low", "cycle": "S2"}
        self.items = [deepcopy(self.item)]; self.states = {s: s for s in t.q.STATES}; self.names = dict(self.states)
        self.members = [{"id": v[1], "email": v[2]} for v in t.q.PEOPLE.values()]; self.blocked = "BLOCKED-LABEL"; self.patches = []
    def issue(self, i): return deepcopy(self.item)
    def refresh_items(self): return self.items
    def patch(self, before, target):
        body = t.patch_body(before, target, self.states, self.blocked); self.patches.append(body); self.item.update(body)
class GH:
    def __init__(self):
        self.pr_data = {"number": case["pr"], "base": {"repo": {"full_name": "Asperant/critical-aerospace-manufacturing"}, "ref": "main"},
            "user": {"login": t.GITHUB[PROFILE]}, "head": {"ref": "wp/WP-SIM-001-deterministic-des-kernel", "sha": case["pr_head_sha"]},
            "title": "[WP-SIM-001] Deterministic DES kernel", "body": "b", "changed_files": case["changed_files"], "state": "closed",
            "merged": True, "merge_commit_sha": case["merge_sha"]}
        self.rows = [{"filename": f"services/manufacturing-simulator/f{i}.py", "status": "added"} for i in range(case["changed_files"] - 1)] + [{"filename": "evidence/WP-SIM-001/README.md", "status": "added"}]
        self.runs = {x["run_id"]: {"id": x["run_id"], "head_sha": case["merge_sha"], "head_branch": "main", "event": "push", "path": x["workflow_path"],
            "status": "completed", "conclusion": "success", "run_started_at": "2026-10-24T12:00:00Z", "updated_at": "2026-10-24T12:30:00Z",
            "repository": {"full_name": "Asperant/critical-aerospace-manufacturing"}} for x in case["validating_runs"]}
    def invalidate(self): pass
    def pr(self, n): return deepcopy(self.pr_data)
    fresh_pr = pr
    def commit(self, sha): return {"sha": sha, "parents": [{"sha": p} for p in case["parents"]]}
    def ancestor(self, a, b): pass
    def main_sha(self): return "f" * 40
    def branch_deleted(self, b): pass
    def files(self, pr): return deepcopy(self.rows)
    def fresh_run(self, n): return deepcopy(self.runs[n])
logs = []
env = {"reason": "Reconcile merged PR 52 into Plane (offline fixture)", "evidence_refs": [f"pr:{case['pr']}"] + [f"run:{x['run_id']}" for x in case["validating_runs"]]}
plane = Plane("READY")
res = r.reconcile(PROFILE, WP, "VALIDATING", env, policy, plane, GH(), lambda rec, key: logs.append(deepcopy(rec)), "k", now=lambda: "2026-10-24T20:00:00+00:00")
out["offline_reconcile"] = {"result": res["result"], "patches": plane.patches, "audit_results": [x["result"] for x in logs],
    "operation": res["operation"], "skipped_state_history_not_asserted": res["skipped_state_history_not_asserted"], "outstanding": res["outstanding"]}
print(json.dumps(out, indent=2))
