Offline project tooling for **CTRL-PM-001…005**, control items outside the 179 canonical WPs.

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
