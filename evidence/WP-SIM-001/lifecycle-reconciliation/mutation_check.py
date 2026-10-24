"""Mutation sensitivity check for the lifecycle-reconciliation tests (run from repo root)."""
import pathlib, shutil, subprocess, sys

REPO = pathlib.Path.cwd()
SCRATCH = pathlib.Path(sys.argv[1]) / "mut-reconcile"
MUT = {
 "R01 DONE accepted as a source": ("reconcile.py", "SOURCES = (", "SOURCES = ('DONE', "),
 "R02 blocker check removed": ("reconcile.py", "    need(plane.blocked not in item[\"labels\"], \"ACTIVE_BLOCKER_UNRESOLVED\")", "    pass"),
 "R03 parent equality removed": ("reconcile.py", "    need(parents == case[\"parents\"], \"MERGE_PARENT_MISMATCH\")", "    pass"),
 "R04 cancelled run qualifies": ("reconcile.py", "TERMINAL_RUN_CONCLUSIONS = (\"success\", \"failure\", \"timed_out\")", "TERMINAL_RUN_CONCLUSIONS = (\"success\", \"failure\", \"timed_out\", \"cancelled\")"),
 "R05 queued run qualifies": ("reconcile.py", "STARTED_RUN_STATUSES = (\"in_progress\", \"completed\")", "STARTED_RUN_STATUSES = (\"in_progress\", \"completed\", \"queued\")"),
 "R06 Plane concurrency check removed": ("reconcile.py", "    need(fresh == item, \"CONCURRENT_PLANE_CHANGE\")", "    pass"),
 "R07 GitHub recheck removed": ("reconcile.py", "    need(stable(again) == stable(facts), \"CONCURRENT_GITHUB_CHANGE\")", "    pass"),
 "R08 evidence refs not checked": ("reconcile.py", "    need(\n        set(envelope[\"evidence_refs\"]) == expected_refs(case, target),\n        \"RECONCILIATION_EVIDENCE_REFS_MISMATCH\",\n    )", "    pass"),
 "R09 scope prefix not required": ("reconcile.py", "            \"WP_SCOPE_PATH_MISSING\",", "            \"WP_SCOPE_PATH_MISSING\",  # mutated\n        ) if False else (None,"),
 "R10 second parent not checked": ("reconcile.py", "        need(parents[1] == pr[\"head\"][\"sha\"], \"MERGE_SECOND_PARENT_NOT_PR_HEAD\")", "        pass"),
 "R11 main reachability removed": ("reconcile.py", "    gh.ancestor(sha, main)  # the merge is reachable from current main", "    pass"),
 "R12 success not required": ("reconcile.py", "        if case[\"require_successful_runs\"]:", "        if False:"),
 "R13 idempotent case rewrites": ("reconcile.py", "    if source == target:", "    if False:"),
 "R14 audit INTENT skipped": ("reconcile.py", "    record[\"result\"] = \"INTENT\"\n    audit(record, key)", "    record[\"result\"] = \"INTENT\""),
 "R15 PATCH sent twice": ("reconcile.py", "            plane.patch(fresh, target)", "            plane.patch(fresh, target)\n            plane.patch(fresh, target)"),
 "R16 owner check weakened": ("reconcile.py", "        need(owner == people[case[\"profile\"]][0], \"RECONCILIATION_OWNER_MISMATCH\")", "        pass"),
 "P01 no terminal-page proof": ("transition.py", "            need(self._get(f'{REPO}/pulls/{number}/files?per_page={FILE_PAGE}&page={pages+1}')==[],\n                 'INCOMPLETE_PR_FILE_SCOPE')", "            pass"),
 "P02 duplicate paths allowed": ("transition.py", "        need(len(names)==len(set(names)), 'DUPLICATE_PR_FILE_PATH')", "        pass"),
 "P03 ceiling removed": ("transition.py", "        need(expected<=FILE_PAGE*FILE_PAGE_CEILING, 'PR_FILE_SCOPE_EXCEEDS_CEILING')", "        pass"),
 "P04 inventory change ignored": ("transition.py", "        need(self.fresh_pr(number).get('changed_files')==expected, 'PR_FILE_SCOPE_CHANGED')", "        pass"),
 "P05 page size not checked": ("transition.py", "            need(isinstance(chunk,list) and len(chunk)==min(FILE_PAGE,expected-FILE_PAGE*(page-1)),\n                 'INCOMPLETE_PR_FILE_SCOPE')", "            need(isinstance(chunk,list), 'INCOMPLETE_PR_FILE_SCOPE')"),
 "P06 ordinary squash rule weakened": ("transition.py", "need(len(commit.get('parents',[]))==1, 'NON_SQUASH_MERGE_SHAPE')", "need(len(commit.get('parents',[]))>=1, 'NON_SQUASH_MERGE_SHAPE')"),
 "I01 grant glob": ("install_auto_next.py", "f\"{RECONCILE_LIBEXEC} {profile} {wp} {target}\"", "f\"{RECONCILE_LIBEXEC} {profile} * {target}\""),
 "I02 legacy ailab grant": ("install_auto_next.py", "f\"{profile} ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I \"", "f\"ailab ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I \""),
 "I03 reconcile hash not pinned": ("install_auto_next.py", "    \"reconcile\": RECONCILE_LIBEXEC,\n", ""),
 "G01 invalidate keeps every cached read (R1 reverted)": ("transition.py", "        self.cache.clear()\n        self.cache.update(keep)\n", "        pass\n"),
 "G02 gather does not invalidate (R1 reverted)": ("reconcile.py", "    gh.invalidate()  # only immutable SHA-addressed commits may be served from cache\n", ""),
 "G03 audit keeps first snapshot": ("reconcile.py", "    record[\"facts\"] = again  # the snapshot closest to the write, incl. latest main\n", ""),
 "Q01 entry owner-queue check removed (R2 reverted)": ("reconcile.py", "        need(not owner_queue_conflicts(plane, profile, item), \"OWNER_QUEUE_CONFLICT\")", "        pass"),
 "Q02 pre-write queue recheck removed": ("reconcile.py", "    need(\n        not owner_queue_conflicts(plane, profile, item),\n        \"CONCURRENT_OWNER_QUEUE_CHANGE\",\n    )\n", ""),
 "Q03 pre-write queue not refreshed": ("reconcile.py", "    plane.refresh_items()  # fresh queue snapshot immediately before writing\n", ""),
 "Q04 IN_PROGRESS ignored": ("reconcile.py", "OWNER_QUEUE_STATES = (\"READY\", \"IN_PROGRESS\")", "OWNER_QUEUE_STATES = (\"READY\",)"),
 "Q05 no-op also blocked by queue": ("reconcile.py", "    if source != target:\n        # A no-op is exempt", "    if True:\n        # A no-op is exempt"),
 "H01 Plane read before the second GitHub snapshot (old order)": ("reconcile.py", ["    again = gather(", "    fresh = plane.issue(item[\"id\"])\n    t.own(fresh, profile, wp, policy)\n    need(fresh == item, \"CONCURRENT_PLANE_CHANGE\")\n    record[\"facts\"]"], ["    fresh = plane.issue(item[\"id\"])\n    t.own(fresh, profile, wp, policy)\n    need(fresh == item, \"CONCURRENT_PLANE_CHANGE\")\n    again = gather(", "    record[\"facts\"]"]),
 "H02 no final Plane equality check": ("reconcile.py", "    need(fresh == item, \"CONCURRENT_PLANE_CHANGE\")\n    record[\"facts\"]", "    record[\"facts\"]"),
 "L01 launcher accepts DONE": ("cap-plane-reconcile", "    MERGED|VALIDATING) ;;", "    MERGED|VALIDATING|DONE) ;;"),
}
def build(mutation=None):
    shutil.rmtree(SCRATCH, ignore_errors=True)
    (SCRATCH/"tools/host").mkdir(parents=True)
    for d in ("plane-transition","plane-queue"):
        shutil.copytree(REPO/"tools/host"/d, SCRATCH/"tools/host"/d, ignore=shutil.ignore_patterns("__pycache__"))
    for d in ("09_change","project_control"):
        shutil.copytree(REPO/d, SCRATCH/d, ignore=shutil.ignore_patterns("__pycache__","history","documentation-reconciliation"))
    (SCRATCH/"tools/projectctl/src").mkdir(parents=True)
    shutil.copytree(REPO/"tools/projectctl/src/projectctl", SCRATCH/"tools/projectctl/src/projectctl", ignore=shutil.ignore_patterns("__pycache__"))

def run():
    return subprocess.run([sys.executable,"-m","unittest","discover","-s",str(SCRATCH/"tools/host/plane-transition"),"-p","test_*.py"],capture_output=True,text=True,cwd=SCRATCH)

build()
base = run()
print("BASELINE (unmutated copy):", [l for l in base.stderr.splitlines() if l.startswith(("Ran ","FAILED","OK"))])
if base.returncode:
    sys.exit("baseline must pass before mutation results mean anything")
for name,(f,old,new) in MUT.items():
    build()
    path = SCRATCH/"tools/host/plane-transition"/f
    text = path.read_text()
    olds, news = (old, new) if isinstance(old, list) else ([old], [new])
    if any(o not in text for o in olds):
        print("PATTERN-MISSING", name); continue
    for o, n in zip(olds, news):
        text = text.replace(o, n, 1)
    path.write_text(text)
    done = run()
    tail = [l for l in done.stderr.splitlines() if l.startswith(("Ran ","FAILED","OK"))]
    print(("CAUGHT  " if done.returncode else "SURVIVED"), name, tail[-1:] )
