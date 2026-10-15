# CTRL-HOST-002 — Remote SSH live Plane queue

Owner-authorized host/control infrastructure; no product work or Plane mutation.

Run `cap-plane-queue` in a Remote SSH session. It accepts no arguments and uses
`CAP_PROFILE` (`asrin`, `selman`, `batuhan`, `yavuz`). JSON reports `current_task`
(IN_PROGRESS) or `next_task` (READY), live BLOCKED label, exact live cycle, canonical
WP ID/title/owner, and UTC completion timestamp. Multiple IN_PROGRESS or multiple
READY candidates return AMBIGUOUS without choosing. BACKLOG is never selected.
Unavailable transport, incomplete pagination, invalid identity/metadata or unknown
schema returns UNAVAILABLE with no response/exception details. A blocked task is
reported, never silently replaced. Exit 0: OK/NO_TASK; 1: BLOCKED/AMBIGUOUS;
2: UNAVAILABLE/invalid invocation. NO_TASK does not authorize implementation.

## Host boundary

- Public launcher: `/usr/local/bin/cap-plane-queue`, root:root 0755.
- Privileged executable: `/usr/local/libexec/cap-plane-queue`, root:root 0755,
  isolated system Python (`-I`), standard library only, no developer/repo imports.
- `/etc/cap-plane-queue/`: root:root 0700.
- `/etc/cap-plane-queue/credential.json`: root:root 0600. No API key in arguments,
  environment, developer profiles or source. The reference clone's ignored
  `project_control/local/plane.env` was migrated here and removed. Existing local
  projectctl Plane commands that expected that file now require separate owner
  administration; the developer queue uses only this helper.
- `/etc/cap-plane-queue/catalog.json`: root-owned static canonical WP/owner identity
  allowlist and source hashes generated from projectctl; no execution state/cache.
  Refresh through reviewed root installation if canonical identity changes.
- `/etc/sudoers.d/cap-plane-queue`: root:root 0440. Only four exact helper command
  lines are granted NOPASSWD, with a NOSETENV rule. This host uses sudo-rs;
  it explicitly ignores `-E` (does not preserve the requested environment).
  This behavior is not relied on as a security control. The executable
  independently ignores Python startup environment (`-I`) and clears its
  environment before accessing credentials or making requests. No shell, interpreter, URL, request
  method, endpoint, query or extra argument is granted. `visudo -cf` is required.
- The root helper sends only literal GET requests to a fixed loopback API v1 origin
  and fixed project/resource allowlist. Fixed known cycle IDs resolve live cycle
  memberships (issue lists omit these). Redirects and environment proxies disabled.
  Only validated pagination cursor data from Plane is added internally. No retries
  or mutations; failures close access. Requests paced at >=1.25 seconds, timeout
  10 seconds, bounded pages/body sizes. Each invocation reads fresh data; no cache. A root-only lock in `/run`
  serializes concurrent sessions to respect the shared API rate limit. It stores
  no execution data; concurrent callers may wait for previous reads to complete.
- Output whitelists fields, removes control/format characters, JSON-escapes text,
  limits titles, and refuses output containing the credential. No response-body or
  exception logging; no tracebacks; core dumps disabled in the privileged helper.

All profiles share Unix UID ailab. CAP_PROFILE is display scope, not authentication
or a security boundary: a caller may read another profile's sanitized queue. The
helper protects the API credential from ordinary unprivileged filesystem access;
it cannot restrict a person who already possesses independent full sudo/root
access. Remote SSH, GitHub/Codex profile isolation and existing sudo rules remain
unchanged. No active developer workspace is inspected or modified by installation.

## Install and verify

From the reference clone's dedicated control branch, run offline validation and
produce the static identity allowlist (outside the repository):

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from projectctl.project import load_project
import json
p = load_project(Path('/srv/ailab/project'))
assert p.summary()['validation'] == 'PASS'
Path('/srv/ailab/remote-ssh/staging/plane-queue-catalog.json').write_text(json.dumps({
    'owners': {w.id: w.primary_owner.canonical_name for w in p.catalog.work_packages},
    'source_manifest': p.source_manifest}, ensure_ascii=False, sort_keys=True))
PY
sudo python3 -I /srv/ailab/project/tools/host/plane-queue/install.py
```

Installer is idempotent: preserves existing root credential, refreshes only managed
helper/catalog/sudo rules and validates sudo syntax. First installation migrates
the existing reference-clone credential without printing it. It never visits
`/srv/ailab/workspaces/`, restarts SSH/services or calls Plane.

```bash
python3 -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -v
CAP_PROFILE=asrin cap-plane-queue
CAP_PROFILE=selman cap-plane-queue
CAP_PROFILE=batuhan cap-plane-queue
CAP_PROFILE=yavuz cap-plane-queue
```

Smoke readbacks describe observations only. Another active developer may legitimately
change execution state concurrently; never overwrite live data to match a snapshot.
For rollback, an owner can remove only `/etc/sudoers.d/cap-plane-queue` to disable
unprivileged access; keep the credential protected. No Plane rollback is needed.
There is no automatic privilege or credential-rotation management.
