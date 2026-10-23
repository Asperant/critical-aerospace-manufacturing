# CTRL-HOST-005 / CHG-020 — proactive derived preparation

Production operational control requested by the project owner on 23 October 2026.
Base fetched before implementation: 734ce53f48dda84fc617159894ade4f558bb8111.
No product WP implementation or evidence assessment is asserted by this change.

The existing resolver eligibility predicate is shared by AUTO_NEXT and preflight.
PREPARED is derived and never written to Plane. The evidence adapter applies the
existing evaluator to a copy of the current-work inventory, with active work only
hypothetically completed. No transition executor is called on the health path.
The top three backlog candidates expose exact unverified DoR criteria and canonical
HARD START readiness nodes/levels/attributable owners. The first eligible preference
fills the buffer even beyond those three or across cycles. UNKNOWN fails closed.
Idle eligible backlog remains STALL_RISK until guarded release; no-task blocked
backlog is STALLED. GitHub identity/auth is read as each actual Unix account.

Focused local validation (real execution, no production mutation):
- Resolver/derived health: 47 passed.
- Host transition/health integration: 92 passed.
- Queue compatibility/isolation: 17 passed.
- Canonical validation PASS; catalog lint PASS (306 records, history checked).
- Static ratchet PASS: unchanged 307 Ruff / 189 Pyright / 56 legacy format findings.
- Flake governance PASS; contract checks PASS; compileall and git diff --check PASS.
- Full local suite deliberately not run; normal required GitHub CI gates merge.

Existing Asrin audit files preserved byte-for-byte:
- projectctl-audit-addendum-2026-10-20-944fd56.md:
  c5ce7e4ee5c3ca4783d84266de79d53c627180ded3c8bb7c620189d8d1f8a181
- projectctl-technical-audit-2026-10-20-944fd56.md:
  53641c2313f08c1282cf7369d043366579028122a6e179ac2f7423502577dad1

Deployment uses actual merged reference source, root-only timestamped helper/unit/
policy backups and rollback, exact sudo grants, source/helper hash verification,
and only systemd daemon-reload plus the new read-only timer enablement.
The timer calls health only, with bounded timeouts, nonblocking shared lock,
atomic 0600 root-only state and aggregate-only journald output. Failed reads publish
UNAVAILABLE. Installed/live verification is recorded separately on the host after
merge; this source record does not claim an unperformed rollout or CI result.
