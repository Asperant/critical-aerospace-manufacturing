# CTRL-HOST-002 — Read-only developer Plane queue

Date: 2026-10-15 (Europe/Istanbul). Owner request authorizes host/control setup,
read-only Plane access and a separate reference-clone control branch/PR. No product
WP implementation is included. No active developer workspace was inspected,
modified, switched, fetched or pulled, including Asrın's WP-GOV-001 workspace.

## Deployed behavior

`cap-plane-queue` accepts no arguments and uses CAP_PROFILE. Root authorization
permits four exact profile command lines only. The API v1 origin is fixed loopback,
the project is fixed Graduation Project / CAP, and resources are allowlisted.
The root helper has exactly one HTTP request construction with literal GET and no
request body. Redirects/proxies are disabled; API-supplied pagination cursors are
validated and bounded. There are no Plane mutation code paths or CLI switches.

The key was migrated from the reference clone's ignored local env file into
`/etc/cap-plane-queue/credential.json`, root:root 0600, parent root:root 0700.
The old ignored reference-clone env file was removed. The key was never printed,
passed in argv or developer environment, or written to this branch/evidence.
No developer workspace or CODEX_HOME was visited for credential installation.

Only IN_PROGRESS / READY can be selected, in that order. Multiple IN_PROGRESS or
multiple READY candidates produce AMBIGUOUS; BACKLOG never supplies a fallback.
The existing BLOCKED label is reported independently. Failed transport, unknown
schema, incomplete pagination or identity disagreement produces UNAVAILABLE.
Static canonical WP/owner identity allowlist is generated with existing projectctl;
execution state is always read live, not stored as another management database.

## Executed verification

- `python3 -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -v`:
  **13 passed** (selection/ambiguity/blockers, sanitation and sentinel-secret guard,
  GET-only request AST and captured transport, route/cursor allowlists, redirects,
  response bounds/timeouts, pagination completeness/duplicates, HTML/JSON metadata,
  invalid invocation, sanitized exceptions, canonical ownership/identity checks).
- Full existing projectctl suite: **205 passed**; canonical validation **PASS**.
- `git diff --check`: PASS. `docs/` unchanged.
- Installer executed twice; root ownership and permissions verified, both sudoers
  syntax checks PASS. Installed helper SHA-256 matches reviewed source.
- Unprivileged credential read and helper write: DENIED. NOPASSWD extra arguments,
  arbitrary shell and arbitrary Python invocations: DENIED.
- Actual key scan against helper sources, sanitized smoke outputs and recent
  system journal: no matches. No secret-bearing exceptions or responses printed.
- All four live profile invocations completed without stderr. See adjacent JSON
  for exact task fields, owners, cycles, blocker flags and UTC read timestamps.
- RustDesk active PID 1785 and Tailscale active PID 1154321 remained unchanged;
  all four personal SSH sockets remained active. No SSH service/config changes,
  Docker/product-service starts, repository-local identity changes or Plane writes.

## Live Plane before / after

Both full canonical WP readbacks observed **179 WPs: 177 BACKLOG, 1 IN_PROGRESS,
1 READY**. The active developer had already moved WP-GOV-001 to IN_PROGRESS;
no historical 2 READY assumption was imposed.

Canonical WP ID, title, assignment/profile, state, BLOCKED flag and exact cycle
readback digest before/after:
`f7f26e6fd776018cebd5a9255bfaffb3d0d4a92b85f43c18258ec2ff564b73f5`.
**UNCHANGED**. Each comparison read used 19 GETs, no other HTTP method.
No claim of atomic transactional snapshot or product WP completion is made.

| Profile | Observed queue | Cycle | BLOCKED |
|---|---|---|---|
| asrin | current_task WP-GOV-001 / IN_PROGRESS | S1 | false |
| selman | NO_TASK | — | — |
| batuhan | NO_TASK | — | — |
| yavuz | next_task WP-CICD-001 / READY | S1 | false |

## Observations and limits

Initial overlapping live probes produced UNAVAILABLE for two profiles. The final
helper serializes complete reads with a root-only `/run` lock to avoid concurrent
API rate bursts; all four final smoke reads passed. There is no cached queue.
Concurrent invocations may wait for preceding reads to finish.

An initial boundary-test expectation that `sudo -E` would be rejected was incorrect:
sudo-rs 0.2.13 explicitly ignores `-E`. It did not preserve the requested environment.
The corrected boundary does not rely on that option: Python -I ignores startup
injection and the helper clears environment before reading the key/requesting data.
No general sudo rights were added. Existing password-authorized full sudo remains
outside this helper's security boundary.

All profiles share UID ailab. CAP_PROFILE scopes sanitized display, not identity
or access control between people. Existing full root/sudo authority can bypass
ordinary filesystem permissions. No audit of other active workspace secrets was
performed, because those workspaces are expressly out of scope.

AGENTS.md now requires queue -> exact canonical WP context -> appropriate live
state/DoR before implementation, and prohibits agent Plane mutation. Host tests
are included in the existing CI workflow. Canonical project documents/counts and
product implementation are unchanged.

Change classification: compatible host/control tooling (C1); credential/sudo
boundary is security-sensitive (CR-3). Separate control PR is for independent
review; no merge or review fabrication is authorized by this task. Historical
setup completion claims are not expanded by this evidence.
