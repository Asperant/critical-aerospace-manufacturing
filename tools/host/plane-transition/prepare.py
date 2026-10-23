#!/usr/bin/python3 -I
"""Root-owned bounded preparation controller. GitHub writes run as real Asrin UID."""

import base64
import fcntl
import importlib.util
import json
import os
import pwd
import resource
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

STATE = Path("/var/lib/cap-plane-prepare")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def persist(path, data):
    fd, name = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, sort_keys=True, ensure_ascii=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(name, path)


def snapshot(plane):
    return {
        x["external_id"]: {
            "state": plane.names[x["state"]],
            "protected_digest": __import__("hashlib")
            .sha256(
                json.dumps(
                    {
                        k: value
                        for k, value in x.items()
                        if k
                        not in {"state", "updated_at", "updated_by", "completed_at"}
                    },
                    sort_keys=True,
                ).encode()
            )
            .hexdigest(),
        }
        for x in plane.items
    }


class Writer:
    """No credentials copied; gh loads only Asrin's existing private profile after drop."""

    def __init__(self, t):
        self.t = t
        self.gh = t.GitHub("asrin")
        self.prewrite = lambda: None

    def call(self, method, route, body=None):
        self.t.need(
            method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
            and route.startswith(self.t.REPO + "/"),
            "INVALID_PREPARATION_ROUTE",
        )
        if method != "GET":
            self.prewrite()
        command = [
            "/usr/bin/gh",
            "api",
            "--hostname",
            "github.com",
            "--method",
            method,
            route,
        ]
        if body is not None:
            command += ["--input", "-"]
        account = pwd.getpwnam("asrin")
        result = subprocess.run(
            command,
            input=None if body is None else json.dumps(body).encode(),
            capture_output=True,
            timeout=35,
            env=self.gh.env,
            cwd="/srv/ailab/workspaces/asrin/project",
            user=account.pw_uid,
            group=account.pw_gid,
            extra_groups=(),
            umask=0o077,
        )
        self.t.need(
            result.returncode == 0 and len(result.stdout) <= 2_000_000,
            "PREPARATION_GITHUB_WRITE_OR_READ_UNCONFIRMED",
        )
        self.gh.cache.clear()
        return json.loads(result.stdout) if result.stdout.strip() else {}


def prepare_pr(t, engine, writer, candidate, plan, policy, before_write):
    """One open PR per WP; a lost response is discovered, never blindly repeated."""
    writer.prewrite = before_write
    wp = candidate["wp_id"]
    repo = t.REPO
    target = engine.path_for(wp)
    branch = "wp/" + wp + "-auto-prepare-" + plan["input_digest"][:12]
    main = writer.gh.main_sha()
    t.need(main == plan["source_sha"], "CONCURRENT_MAIN_CHANGE_RECOMPUTE_REQUIRED")
    # A canonical-same preparation survives unrelated main commits; verify each use.
    tree = writer.call("GET", f"{repo}/git/trees/{main}?recursive=1")
    t.need(tree.get("truncated") is False, "REPOSITORY_TREE_INCOMPLETE")
    if any(x["path"] == target for x in tree["tree"]):
        raw = writer.gh.evidence_text(target, main)
        prior = json.loads(raw)
        if prior == engine.derive(policy["contexts"][wp], policy, prior["source_sha"]):
            return {"state": "ALREADY_PRESENT", "wp_id": wp}
        return {
            "state": "REAL_WORK_REQUIRED",
            "wp_id": wp,
            "reason": "EXISTING_PREPARATION_INPUT_CHANGED_REVIEW_REQUIRED",
        }
    prs = writer.call("GET", f"{repo}/pulls?state=open&per_page=100")
    t.need(len(prs) < 100, "PREPARATION_PR_DISCOVERY_INCOMPLETE")
    active = [
        p for p in prs if p["head"]["ref"].startswith("wp/" + wp + "-auto-prepare-")
    ]
    t.need(len(active) <= 1, "DUPLICATE_PREPARATION_PRS")
    if active:
        pr = writer.call("GET", f"{repo}/pulls/{active[0]['number']}")
        t.need(
            pr["head"]["ref"] == branch,
            "EXISTING_PREPARATION_INPUT_CHANGED_REVIEW_REQUIRED",
        )
    else:
        closed = writer.call(
            "GET", f"{repo}/pulls?state=closed&head=Asperant:{branch}&per_page=1"
        )
        if closed:
            return {
                "state": "REAL_WORK_REQUIRED",
                "wp_id": wp,
                "reason": "PREVIOUS_PREPARATION_CLOSED_NO_BLIND_RETRY",
                "pr": closed[0]["number"],
            }
        refs = writer.call("GET", f"{repo}/git/matching-refs/heads/{branch}")
        exact = [x for x in refs if x["ref"] == "refs/heads/" + branch]
        if not exact:
            route = writer.call("GET", f"{repo}/contents/.github/CODEOWNERS?ref={main}")
            owners = base64.b64decode(route["content"]).decode()
            names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
            line = engine.routing_line(policy["contexts"][wp], names)
            owners = owners.rstrip() + "\n" + line + "\n"
            before_write()
            t.need(
                writer.gh.main_sha() == main,
                "CONCURRENT_MAIN_CHANGE_RECOMPUTE_REQUIRED",
            )
            newtree = writer.call(
                "POST",
                f"{repo}/git/trees",
                {
                    "base_tree": tree["sha"],
                    "tree": [
                        {
                            "path": target,
                            "mode": "100644",
                            "type": "blob",
                            "content": engine.encode(plan),
                        },
                        {
                            "path": ".github/CODEOWNERS",
                            "mode": "100644",
                            "type": "blob",
                            "content": owners,
                        },
                    ],
                },
            )
            commit = writer.call(
                "POST",
                f"{repo}/git/commits",
                {
                    "message": f"[{wp}] Derive bounded canonical START preparation (CTRL-HOST-006)",
                    "tree": newtree["sha"],
                    "parents": [main],
                },
            )
            before_write()
            writer.call(
                "POST",
                f"{repo}/git/refs",
                {"ref": "refs/heads/" + branch, "sha": commit["sha"]},
            )
        before_write()
        pr = writer.call(
            "POST",
            f"{repo}/pulls",
            {
                "title": f"[{wp}] Canonical automatic START preparation",
                "head": branch,
                "base": "main",
                "body": f"WP: {wp}\nControl: CTRL-HOST-006 / CHG-021\nSource: {main}\n\nCanonical metadata and planned workstream only. No implementation, test result or readiness artifact is certified. Deterministic generation and fresh transition validation are mandatory. CHG-018: zero development approvals; all required CI retained.",
            },
        )
    # Bind exact minimal diff and authenticated Asrin author, even on recovery.
    t.need(
        pr["user"]["login"].casefold() == t.GITHUB["asrin"].casefold()
        and not pr["draft"]
        and pr["base"]["ref"] == "main",
        "PREPARATION_PR_SCOPE_INVALID",
    )
    head = pr["head"]["sha"]
    files = writer.call("GET", f"{repo}/pulls/{pr['number']}/files?per_page=100")
    t.need(
        {x["filename"] for x in files} == {target, ".github/CODEOWNERS"}
        and len(files) == 2,
        "PREPARATION_PR_DIFF_INVALID",
    )
    stored = json.loads(writer.gh.evidence_text(target, head))
    t.need(
        stored == engine.derive(policy["contexts"][wp], policy, stored["source_sha"]),
        "PREPARATION_PR_CONTENT_CHANGED",
    )
    # Exact CODEOWNERS diff only appends the deterministic routing line.
    old_route = writer.call(
        "GET",
        f"{repo}/contents/.github/CODEOWNERS?ref={pr['base'].get('sha', stored['source_sha'])}",
    )
    new_route = writer.call("GET", f"{repo}/contents/.github/CODEOWNERS?ref={head}")
    names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
    expected_route = (
        base64.b64decode(old_route["content"]).decode().rstrip()
        + "\n"
        + engine.routing_line(policy["contexts"][wp], names)
        + "\n"
    )
    t.need(
        base64.b64decode(new_route["content"]).decode() == expected_route,
        "PREPARATION_ROUTING_DIFF_INVALID",
    )
    comparison = writer.call("GET", f"{repo}/compare/main...{head}")
    if comparison.get("behind_by", 0) > 0:
        before_write()
        writer.call(
            "PUT",
            f"{repo}/pulls/{pr['number']}/update-branch",
            {"expected_head_sha": head},
        )
        return {
            "state": "IN_PROGRESS",
            "wp_id": wp,
            "pr": pr["number"],
            "reason": "BASE_UPDATED_REQUIRED_CI_PENDING",
        }
    try:
        t.ci(writer.gh, head, policy)
    except t.Denied as exc:
        return {
            "state": "IN_PROGRESS",
            "wp_id": wp,
            "pr": pr["number"],
            "reason": exc.code,
        }
    writer.gh.cache.clear()
    fresh = writer.call("GET", f"{repo}/pulls/{pr['number']}")
    t.need(
        fresh["head"]["sha"] == head
        and fresh["mergeable"] is True
        and fresh.get("mergeable_state") == "clean",
        "PREPARATION_PR_NOT_MERGEABLE",
    )
    comparison = writer.call("GET", f"{repo}/compare/main...{head}")
    t.need(comparison.get("behind_by") == 0, "PREPARATION_PR_BEHIND_MAIN")
    before_write()
    merged = writer.call(
        "PUT",
        f"{repo}/pulls/{pr['number']}/merge",
        {"sha": head, "merge_method": "squash"},
    )
    t.need(merged.get("merged") is True, "PREPARATION_MERGE_UNCONFIRMED")
    return {"state": "MERGED", "wp_id": wp, "pr": pr["number"], "sha": merged["sha"]}


def run(auto, t, engine, policy, key):
    results = {}
    writer = None
    pending = False
    initial = t.Plane(key)
    persist(STATE / "before.json", snapshot(initial))
    profiles = ["asrin", "yavuz", "batuhan", "selman"]
    replenished = set()
    for profile in profiles:
        health = auto.owner_health(t, profile, policy, t.Plane(key), t.GitHub)
        actions = []
        if health["health"] != "UNAVAILABLE":
            for candidate in health["candidates"][:3]:
                try:
                    gh = t.GitHub(profile)
                    sha = gh.main_sha()
                    plan = engine.derive(
                        policy["contexts"][candidate["wp_id"]], policy, sha
                    )
                    state = engine.classify(candidate, plan)
                    if pending and state == "AUTO_PREPARABLE":
                        actions.append(
                            {
                                "wp_id": candidate["wp_id"],
                                "state": "IN_PROGRESS",
                                "reason": "SERIAL_PREPARATION_PR_PENDING",
                            }
                        )
                        continue
                    if state != "AUTO_PREPARABLE":
                        actions.append(
                            {
                                "wp_id": candidate["wp_id"],
                                "state": state,
                                "reason": candidate["reason"],
                                "hard_start_blockers": candidate["hard_start_blockers"],
                                "unknown_criteria": [
                                    k
                                    for k, v in plan["checks"].items()
                                    if v["result"] == "UNKNOWN"
                                ],
                            }
                        )
                        continue
                    wp = candidate["wp_id"]
                    fd = os.open(
                        STATE / (wp + ".lock"),
                        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
                        0o600,
                    )
                    with os.fdopen(fd, "r+") as lock:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        observed = auto.live_view(t, t.Plane(key), policy)

                        def before_write(observed=observed, sha=sha):
                            t.verify_policy_sources(policy)
                            t.need(
                                auto.live_view(t, t.Plane(key), policy) == observed,
                                "CONCURRENT_PLANE_CHANGE_RECOMPUTE_REQUIRED",
                            )
                            fresh = t.GitHub("asrin")
                            t.need(
                                fresh.main_sha() == sha,
                                "CONCURRENT_MAIN_CHANGE_RECOMPUTE_REQUIRED",
                            )

                        if writer is None:
                            writer = Writer(t)
                        writer.gh.cache.clear()
                        action = prepare_pr(
                            t, engine, writer, candidate, plan, policy, before_write
                        )
                        actions.append(action)
                        persist(STATE / (wp + ".json"), action)
                        # Only one PR creation/merge per run: prevents parallel-base conflicts.
                        if action["state"] in {"IN_PROGRESS", "MERGED"}:
                            pending = action["state"] == "IN_PROGRESS"
                            break
                except Exception as exc:
                    actions.append(
                        {
                            "wp_id": candidate["wp_id"],
                            "state": "UNAVAILABLE",
                            "reason": getattr(
                                exc,
                                "code",
                                "PREPARATION_FAILED_REQUIRES_FRESH_RECOMPUTE",
                            ),
                        }
                    )
                    break
        # Same existing guarded AUTO_NEXT; current work always prevents another READY.
        decision = auto.advance_owner(
            t, profile, policy, lambda: t.Plane(key), t.GitHub, t.append_audit, key
        )
        if (
            decision.get("transition_result") == "VERIFIED"
            and profile not in replenished
        ):
            profiles.append(profile)
            replenished.add(profile)
        fresh_health = auto.owner_health(t, profile, policy, t.Plane(key), t.GitHub)
        if any(a["state"] == "IN_PROGRESS" for a in actions) and not fresh_health.get(
            "prepared_next"
        ):
            fresh_health["preparation"] = "IN_PROGRESS"
        results[profile] = {
            "actions": actions,
            "auto_next": decision,
            "health": fresh_health,
        }
        persist(STATE / "latest.json", {"timestamp": t.now(), "profiles": results})
    final = snapshot(t.Plane(key))
    persist(STATE / "after.json", final)
    before = snapshot(initial)
    changes = {
        wp: {"before": before[wp], "after": final[wp]}
        for wp in before
        if before[wp] != final[wp]
    }
    return {"timestamp": t.now(), "profiles": results, "production_diff": changes}


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    signal.alarm(720)
    if (
        os.geteuid() != 0
        or sys.argv[1:] != ["--all"]
        or int(os.environ.get("SUDO_UID", "0")) != 0
    ):
        return 2
    os.environ.clear()
    os.umask(0o077)
    STATE.mkdir(mode=0o700, exist_ok=True)
    if STATE.is_symlink() or STATE.stat().st_uid != 0 or STATE.stat().st_mode & 0o077:
        return 2
    try:
        auto = load("cap_auto_prepare", "/usr/local/libexec/cap-auto-next.py")
        engine = load("cap_preparation", "/usr/local/libexec/cap-preparation.py")
        t = auto.load_transition()
        policy = json.loads(
            (auto.ROOT / "transition-policy.json").read_text(),
            object_pairs_hook=t.q.unique,
        )
        t.verify_policy_sources(policy)
        t.policy_checks(policy)
        key = json.loads((auto.ROOT / "credential.json").read_text())["api_key"]
        fd = os.open(
            "/run/cap-plane-queue.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "r+") as lock:
            t.need(os.fstat(lock.fileno()).st_uid == 0, "UNSAFE_LOCK_OWNER")
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = run(auto, t, engine, policy, key)
            t.need(key not in json.dumps(result), "UNSAFE_OUTPUT")
            persist(STATE / "latest.json", result)
        print(json.dumps({"result": "EXECUTED", "timestamp": result["timestamp"]}))
        return 0
    except Exception as exc:
        result = {
            "result": "UNAVAILABLE",
            "reason": getattr(exc, "code", "PREPARATION_FAILED_NO_BLIND_RETRY"),
        }
        persist(STATE / "failure.json", result)
        print(json.dumps(result))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
