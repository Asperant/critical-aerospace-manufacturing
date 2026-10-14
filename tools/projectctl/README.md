Offline project tooling, initially for **CTRL-PM-001…005**, control items outside the 179 canonical WPs.

**WP-GOV-001** adds the source-linked requirement catalog, schema, inventory
exports and fail-closed `catalog-lint`. See [the catalog runbook](../../requirements/README.md).
These commands do not certify readiness, completion or accepted evidence.

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
and structured canonical metadata. The human-approved
`human-approved-terminal-target-completion-v1` policy selects the last numbered
cycle for Plane coordination only; the full original sprint window, all canonical
cycle IDs, canonical owner, milestone and source provenance remain in the HTML
description. The five unscheduled WPs receive neither cycle nor milestone label.
Only Asrın's exact project member receives his 73 WPs; the other 106 stay unassigned.
A missing/non-null project default assignee blocks creation.

The exact lexicographically first eligible Asrın single-cycle WP is the permanent
pilot. A checkpoint records its projection before creation; fresh issue and
relationship reads must verify BACKLOG, labels, assignee, full metadata, module
and cycle before bulk import proceeds. Description comparison parses the single
JSON metadata block after HTML normalization; duplicates and corrupted content
fail closed. Labels/assignees are embedded in creation. Only issue POSTs and
single-WP module/cycle association POSTs are allowed; updates, invitations,
blockers, state changes and deletes are unavailable. Existing conflicting
metadata or relationships stop import rather than moving/resetting them.
Ambiguous POSTs reconcile fresh inventory with at most five attempts.

`expected_projection` and `import_plan` produce pure previews;
`WPImport.inventory` and `WPImport.audit` read all module/cycle memberships and,
for complete audits, every issue's relations. Evidence snapshots are reproducible
observations, never an execution database. A fresh second `run` must have no
mutation requests, no conflicts and all 179 issues unchanged. The older generic
`plane-plan` retains its original unapproved multi-cycle behavior; it is not this
explicitly approved policy's executable import plan. No general apply/sync CLI
has been introduced. Import conformity does not certify readiness or completion.

## Fail-closed governance checks

`projectctl check-ready <WP-ID>` and `projectctl check-done <WP-ID>` emit deterministic JSON to stdout. PASS exits 0; FAIL and UNKNOWN exit 1; input-loading failures exit 2. Current evidence support is deliberately unavailable: structurally valid canonical WPs return UNKNOWN, invalid identities/baselines return FAIL. No command can currently produce PASS from planning, merged code, test success or a demo. All applicable docs/08 obligations still require actual execution evidence and confirmations. No Plane calls, state writes, automatic transitions or local execution database are introduced.


Development-review policy validation checks the active static companion
`09_change/development_review_policy.json` against its CHG-018 final owner decision and
canonical docs/01, docs/08 and docs/09 bindings (all development approvals 0; advisory review only). A claimed missing/conflicting companion is an ERROR. This offline
check neither certifies live review/CI/DoD nor grants READY/DONE; the host helper
separately evaluates actual GitHub/Plane facts.
