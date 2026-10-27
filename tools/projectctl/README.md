Offline project tooling, initially for **CTRL-PM-001…005**, control items outside the 179 canonical WPs.

**WP-GOV-001** adds the source-linked requirement catalog, schema, inventory
exports and fail-closed `catalog-lint`. See [the catalog runbook](../../requirements/README.md).
`check-ready` consumes a bound `evidence/<WP-ID>/READY.md` accountable
assessment. It evaluates applicable DOR-TASK and DOR-WP confirmations and only
HARD START-stage dependency edges; INTEGRATION-stage edges remain later gates.
Missing, conflicting or ambiguous evidence remains `UNKNOWN` and is never
promoted to readiness. `check-done` remains fail-closed pending its post-merge
evidence adapter.

With the declared dependencies already available locally:

```sh
python -m pip install --no-index --no-build-isolation -e 'tools/projectctl[test]'
projectctl parse
projectctl validate
projectctl status
projectctl context WP-CORE-001
projectctl next --owner Batu --cycle S2
python -B -m pytest tools/projectctl/tests
```

Alternatively, set `PYTHONPATH=tools/projectctl/src` and run `python -B -m projectctl`.
The CLI discovers the repository from the current directory or accepts `--root`.
`parse` emits JSON; `validate` and `status` also support `--json`.
Offline commands emit to stdout, never save generated state, and use no network clients.

Validation covers WBS, schedule/roadmap agreement, dependency topology and registry
mirrors, canonical requirements and RTM metadata. Architecture references remain
source assertions; existence against the 02 registry is not yet checked.
Semantic findings are WARNING diagnostics for offline inspection, never permission
to satisfy a dependency or certify readiness. Structural/identity/conflicting
metadata errors fail validation. No known-finding suppression or documentation
repair is performed. Requirement revision/status and NFR metadata gaps stay null.

`parse` emits the unified model, source hashes and parser version. `context` shows
canonical WP data, all cycle memberships and relevant unresolved findings. `next`
lists mandatory scheduled planning candidates, without knowledge of execution
state or any readiness certification. No optional/unscheduled work is selected.
Raw expectations and source spans are preserved; lines are locations, not identity.
Raw `NOT_STARTED` never becomes execution state. No sync, READY or DONE operation
exists. All default commands write only to stdout and require no network access.

CTRL-PM-006 adds explicit `projectctl plane-audit`: GET-only API **v1** discovery
using `X-API-Key`. It has no mutation methods or API-version fallback. Configure
PLANE_BASE_URL, PLANE_API_KEY, PLANE_WORKSPACE_SLUG and PLANE_PROJECT_ID in the
environment or ignored `project_control/local/plane.env` (environment wins).
The local file is parsed as literal data, never executed as shell code. Credentials
and member email addresses are omitted from the stdout audit. HTTP bodies and
transport exceptions are omitted from errors; redirects are not followed.
The configured project must resolve to Graduation Project / CAP. A denied direct
workspace endpoint is recorded, with workspace ID checked through the project
and the workspace-scoped project listing. Unsupported optional membership
endpoints produce null, never an assumed empty membership list.

CTRL-PM-007 adds an offline dry-run:

```sh
projectctl plane-plan --audit /explicit/path/to/sanitized-audit.json
```

It never connects to Plane or reads credentials. Output includes all 29 modules,
13 cycles, nine milestone labels, BLOCKED and 179 WPs, plus exact desired static
fields, create/update/unchanged decisions, canonical-ID duplicates, conflicts and
missing owners. Names of modules use stable capability IDs; titles are descriptions.
Only exact normalized full names in project membership qualify for assignment.
Missing members stay unassigned; their canonical names remain in metadata.
New issues alone initialize BACKLOG; updates never reset execution states.
Unmanaged existing descriptions are not overwritten. Multi-cycle windows remain
unresolved; no arbitrary Plane cycle or calendar date is chosen. The generated
preview uses symbolic references for structures that do not exist yet. Relations
are intended mappings, not executable requests. It is not an apply manifest;
re-read identity/membership and verify API relation/date contracts before applying.
Exit zero means a plan was computed; `ready_for_live_mutation` and findings must
be inspected. Pure tests simulate static projection application twice to prove
zero duplicate creates/metadata updates; live relational idempotency is unproven.
No sync/apply or Plane mutation command exists.

CTRL-PM-008 supplies an approval-gated `StructureBootstrap` helper, deliberately
outside the CLI. Its allowlist covers only the approved existing state-name PATCH
and missing capability modules, undated cycles and milestone labels. It never
writes issues, members, relations or calendar dates. Existing structures are
matched by exact stable names; duplicates, extra entities and metadata conflicts
stop the operation. Completed entities survive failures and are skipped on resume.

All Plane API calls use `PlaneStream`, shared by reads and writes. A process-wide
lock serializes requests across clients, with a default 1.25-second minimum
start interval (at most 48 requests/minute). Optional non-secret configuration
`PLANE_REQUEST_INTERVAL_SECONDS` may increase that interval in the environment or
ignored local file. API v1 and X-API-Key remain explicit; redirects are disabled.
The client observes Remaining/Reset/Retry-After headers, honors Retry-After seconds
or HTTP dates, then reset time, then bounded exponential backoff (2–30 seconds).
Remaining=0 delays subsequent requests. Rate-limited GETs and the approved
idempotent name PATCH allow at most five attempts. POSTs never blindly replay:
after a rate limit, transport failure, 5xx or unusable success response, the helper
waits and reads fresh inventory. One exact match reconciles success; zero permits
a bounded retry; duplicate/conflicting matches stop. Retry telemetry contains
only safe method/path/status and parsed timing values, never credentials or bodies.
Live request budgets may also be consumed by other clients; server waits are
respected without changing Plane configuration. Offline commands are unchanged.

CTRL-PM-009 adds the explicitly approval-gated `WPImport` helper outside the CLI.
It imports one canonical WP per issue, with the existing `[WP-ID] title` format
and structured canonical metadata. The approved `approved-single-cycle-v1`
policy selects the first ordered cycle for Plane coordination only; the full
original sprint window, all canonical cycle IDs, canonical owner, milestone and
source provenance remain in the HTML description. The five unscheduled WPs
receive neither cycle nor milestone label. Every canonical owner receives the
verified Plane member assignment; queue profile filtering remains a separate
selection concern.
A missing/non-null project default assignee blocks creation.

The exact lexicographically first eligible Asrın single-cycle WP is the permanent
pilot. A checkpoint records its projection before creation; fresh issue and
relationship reads must verify BACKLOG, labels, canonical owner assignee, full
metadata, module and exactly one approved cycle before bulk import proceeds.
Description comparison parses the single JSON metadata block after HTML
normalization; duplicates and corrupted content fail closed. Labels/assignees
are embedded in creation. The full canonical cycle window remains metadata,
while Plane stores the first ordered cycle as the generic single-cycle
operational projection. Queue selection is profile-scoped and independent from
the global owner assignment projection. Only issue POSTs and single-WP
module/cycle association POSTs are allowed; updates, invitations, blockers,
state changes and deletes are unavailable. Existing conflicting metadata or
relationships stop import rather than moving/resetting them. Ambiguous POSTs
reconcile fresh inventory with at most five attempts.

`expected_projection` and `import_plan` produce pure previews;
`WPImport.inventory` and `WPImport.audit` read all module/cycle memberships and,
for complete audits, every issue's relations. Evidence snapshots are reproducible
observations, never an execution database. A fresh second `run` must have no
mutation requests, no conflicts and all 180 issues unchanged. `plane-plan` and
the approved importer share the same generic single-cycle projection rule. No
general apply/sync CLI has been introduced. Import conformity does not certify
readiness or completion.

## Fail-closed governance checks

`projectctl check-ready <WP-ID>` and `projectctl check-done <WP-ID>` emit deterministic JSON to stdout. PASS exits 0; FAIL and UNKNOWN exit 1; input-loading failures exit 2. `check-ready` can produce PASS only from the supported bound Markdown assessment format; invalid, missing or ambiguous evidence remains UNKNOWN. `check-done` remains fail-closed pending its post-merge evidence adapter. No Plane calls, state writes, automatic transitions or local execution database are introduced.

## CHG-054 / CTRL-HOST-031 — startability

`projectctl startability <WP-ID>` emits `cap-startability-v1` without reading
Plane, READY/DoR evidence, audit history, caches or Slot Release data. It returns
`STARTABLE` only when the canonical WP/owner/scope resolve unambiguously and no
canonical `HARD + START` edge is unresolved. `HARD + INTEGRATION` and later-stage
edges do not block implementation start. This command is a startability
diagnostic, not a DONE or acceptance certification.


Development-review policy validation checks the active static companion
`09_change/development_review_policy.json` against its CHG-018 final owner decision and
canonical docs/01, docs/08 and docs/09 bindings (all development approvals 0; advisory review only). A claimed missing/conflicting companion is an ERROR. This offline
check neither certifies live review/CI/DoD nor grants READY/DONE; the host helper
separately evaluates actual GitHub/Plane facts.


## AUTO_NEXT — CHG-019 / CTRL-HOST-004 (22 October 2026)

Canonical planning preference lives in `project_control/execution_preferences.yaml`.
Every scheduled owned WP appears exactly once; the five unscheduled WPs stay outside.
Earlier milestone/window comes first, then canonical security/data-integrity,
cross-owner enabling and milestone work, then primary work; the owner's roadmap
section 9 order is the explicit final planning tie-breaker. Current broken-main or
security incidents are not invented from titles; actual repair remains governed
by the Task Priority Rule. This artifact is priority only, never readiness/evidence.

AUTO_NEXT scans preference and skips ineligible work with precise reasons. It uses
canonical node readiness and HARD START gates, not producer-WP DONE. Later-stage
HARD gates retain their actual stage; SOFT gaps are visible. UNKNOWN is not PASS.
Existing attributable current-revision DoR/dependency assessments and exact artifacts
are required; automation never generates confirmations or certifies from planning.

Any READY, IN_PROGRESS, IN_REVIEW, MERGE_READY, MERGED or VALIDATING work prevents
automatic release of another READY. BLOCKED active work is surfaced. This conservative
automatic-release policy does not change the global implementation WIP doctrine.
After VERIFIED DONE, the owner and canonical node consumers are evaluated under the
shared lock. Only BACKLOG -> READY may be automatically written, through the existing
transition evaluator, durable INTENT, one PATCH and fresh verified readback. External
writer races fail closed and require recomputation; timeout is never blindly retried.
No assignment, cycle, module, label, title, description or dependency backfill occurs.

Run `cap-plane-queue` in the real account/profile. JSON compatibility is retained;
`display_status` explains CURRENT/READY/NO_TASK/BLOCKED. NO_TASK includes fresh
eligibility reasons; never choose BACKLOG yourself. `projectctl next` remains
planning-only. Recovery: `cap-plane-advance` for own profile; root administration:
`sudo cap-plane-advance --all`. Both use the same resolver and guards. Offline
`projectctl execution-preferences` validates coverage; `queue-preview` reads explicit
live/evidence snapshots and never authorizes or performs a transition.

Separate Linux accounts asrin/selman/batuhan/yavuz and private workspaces/profiles
are authoritative. The helper drops GitHub reads to the matching account; root-only
installed code/policy is used, never writable repository imports. CAP_PROFILE must
match the real sudo caller. Historical shared-ailab descriptions are superseded for
this workflow; no workspace permissions, SSH or profile paths are changed.
CHG-018 zero-development-approval policy remains; product HITL stays unchanged.

Deploy only merged reference source. The dedicated AUTO_NEXT installer creates a
root-only timestamped `/root` backup and rollback script before replacing helper
files, refreshes source/helper hashes, verifies sudoers and preserves audit. Rollback
restores deployment only; never replay a stale Plane DB or state snapshot. No service
restart is required. Missing evidence results in NO_TASK, never synthetic READY.
