"""Mutation check for the CHG-033 recovery proof (WP-SIM-001).

Usage (repository root, locked CI environment):
    python evidence/WP-SIM-001/recovery-proof/mutation_check.py
Copies tools/ and 09_change/ to a scratch directory, injects one defect at a time into the
copy of auto_next.recovery_proof, runs test_recovery there and reports CAUGHT or SURVIVED.
The repository is never modified.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
M = [
    ("expiry", 'today.isoformat() <= disposition["expires_on"]', "True"),
    ("unedited", 'and comment.get("created_at") == comment.get("updated_at")', ""),
    (
        "author",
        '== t.GITHUB[profile].casefold()\n        and comment.get("created_at")',
        '== t.GITHUB[profile].casefold() or True\n        and comment.get("created_at")',
    ),
    (
        "none-field",
        'and exact_field(text, "Owner-executable implementation work") == "NONE"',
        "",
    ),
    ("case-field", 'and exact_field(text, "Recovery case") == case["case_id"]', ""),
    (
        "audit-field",
        'and exact_field(text, "Original blocker audit") == case["blocker_audit_id"]',
        "",
    ),
    (
        "class-field",
        'and exact_field(text, "Deferred acceptance class") == case["classification"]',
        "",
    ),
    ("resolves", 'and exact_field(text, "Resolves blocker") is None', ""),
    (
        "producers-field",
        'and sorted(p.strip() for p in pending.split(","))\n        == sorted(case["pending_producers"])',
        "",
    ),
    ("blocker-eq", 'record.get("blocker") == previous.get("blocker")', "True"),
    (
        "evidence",
        't.need(record["_artifact_refs"], "RECOVERY_EVIDENCE_MISSING")',
        "pass",
    ),
    (
        "artifact-exists",
        "        gh.artifact(ref, sha)\n    main = gh.main_sha()",
        "        pass\n    main = gh.main_sha()",
    ),
    (
        "assessed-on-main",
        "gh.ancestor(sha, main)  # the assessed revision is on main",
        "pass",
    ),
    (
        "scope-assessed",
        "    check_canonical_scope(t, gh, wp, sha, policy)\n    check_canonical_scope(t, gh, wp, main, policy)",
        "    check_canonical_scope(t, gh, wp, main, policy)",
    ),
    (
        "scope-main",
        "    check_canonical_scope(t, gh, wp, sha, policy)\n    check_canonical_scope(t, gh, wp, main, policy)",
        "    check_canonical_scope(t, gh, wp, sha, policy)",
    ),
    (
        "producers-at-main",
        'gh._get(f"{t.REPO}/git/trees/{main}?recursive=1")',
        'gh._get(f"{t.REPO}/git/trees/{sha}?recursive=1")',
    ),
    (
        "disposition-cited",
        "        and exact_field(text, \"Platform disposition\")\n        == f\"PR {disposition['pr']} {disposition['merge_sha']}\"\n",
        "",
    ),
    (
        "delivered",
        'not any(\n            row["path"].startswith(f"evidence/{producer}/")',
        'True or not any(\n            row["path"].startswith(f"evidence/{producer}/")',
    ),
    (
        "disp-merged",
        'pr.get("merged") is True\n        and pr.get("merge_commit_sha") == disposition["merge_sha"]',
        "True\n        and True",
    ),
    (
        "disp-author",
        '== t.GITHUB[disposition["owner"]].casefold(),\n        "RECOVERY_DISPOSITION_UNVERIFIED"',
        '== t.GITHUB[disposition["owner"]].casefold() or True,\n        "RECOVERY_DISPOSITION_UNVERIFIED"',
    ),
    ("disp-anc", 'gh.ancestor(disposition["merge_sha"], main)', "pass"),
    (
        "registry-compare-current",
        "registry_entry(t, gh, disposition, main) == approved",
        "True",
    ),
    (
        "approved-at-merge",
        'registry_entry(t, gh, disposition, disposition["merge_sha"])',
        "registry_entry(t, gh, disposition, main)",
    ),
    ("unique-entry", "t.need(len(found) == 1,", "t.need(len(found) >= 1,"),
    (
        "approved-owner",
        'and exemption.get("owner") == t.q.PEOPLE[disposition["owner"]][0].split()[0]\n        ',
        "",
    ),
    (
        "approved-expiry",
        '\n        and exemption.get("expires_on") == disposition["expires_on"]',
        "",
    ),
    ("exemption-is-dict", "isinstance(exemption, dict)\n        and ", ""),
    ("audit-mismatch", 'previous.get("audit_id") == case["blocker_audit_id"]', "True"),
    (
        "audit-verified",
        'previous.get("result") == "VERIFIED"\n        and previous.get("operation") == "BLOCKED"\n        and previous.get("from_state") == "VALIDATING"\n        and previous.get("to_state") == "VALIDATING"\n        and previous.get("profile") == profile,\n        "RECOVERY_BLOCKER_AUDIT_MISSING"',
        'True,\n        "RECOVERY_BLOCKER_AUDIT_MISSING"',
    ),
    (
        "gather",
        '    reconcile.gather(gh, base, profile, wp, "VALIDATING")  # PR, merge, scope, runs\n',
        "",
    ),
    (
        "reassertion",
        't.need(len(ids) == 1, "RECOVERY_ASSESSMENT_REQUIRED")',
        'ids = ids or ["222"]',
    ),
]

with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    shutil.copytree(
        REPO / "tools", work / "tools", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(REPO / "09_change", work / "09_change")
    target = work / "tools/host/plane-transition/auto_next.py"
    original = target.read_text()
    start = original.index("def registry_entry")
    end = original.index("def discover(gh, t):")
    survivors = 0
    for name, old, new in M:
        body = original[start:end]
        if body.count(old) != 1:
            print("SKIPPED (anchor not found)", name)
            survivors += 1
            continue
        target.write_text(original[:start] + body.replace(old, new) + original[end:])
        done = subprocess.run(
            [sys.executable, "-m", "unittest", "test_recovery"],
            cwd=work / "tools/host/plane-transition",
            capture_output=True,
        )
        caught = done.returncode != 0
        survivors += not caught
        print("CAUGHT  " if caught else "SURVIVED", name)
    print(f"mutants: {len(M)}, survivors or skipped: {survivors}")
