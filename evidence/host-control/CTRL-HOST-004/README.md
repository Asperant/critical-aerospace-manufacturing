# CTRL-HOST-004 / CHG-019 — guarded automatic next work

Canonical 174-WP preference, pure first-eligible resolver, guarded transition
reuse, verified-DONE and contract/blocker-resolution reevaluation, own-profile
and root recovery, read-only queue explanations, separate-account enforcement,
and merged-source installer with root-only backup/rollback are implemented.

Local final checks: 329 projectctl tests (including 34 resolver cases), 86 host
transition/orchestration tests, 17 queue tests, 26 CI-tooling tests: 458 passed,
zero failed/skipped. Results and exact command logs accompany this file. Static
ratchet, schemas, flake governance, canonical validation, preference coverage,
catalog history and whitespace checks passed. Earlier failures identified a
changed master-document provenance hash, fixture assumptions and static typing;
no governance/test threshold was weakened. Catalog regeneration changed only
source provenance, preserving all 306 requirement definitions. Static baseline
only tightened existing import findings.

Mutation/race cases use offline fixtures. A real OS flock test serializes two
advances through the real transition engine and proves one READY PATCH. Tests
cover missing DoR/readiness, later-stage and SOFT gates, producer-DONE insufficiency,
active/pending preservation, source/identity drift, external writer changes,
timeout/readback, audit failure, scoped affected owners and no protected-field writes.
Production Plane lifecycle was not exercised as a destructive test.

The two pre-existing untracked developer audit files retain their recorded SHA256.
Separate UIDs, SSH/profile paths and workspace permissions were not changed.

Predeployment GitHub identity reads verified Asrin/Asperant, Batuhan/Ejlonn and
Yavuz/Yavuzgmus. Selman/selorito's existing isolated login returns HTTP 401; the
project owner explicitly deferred his authentication verification in this session.
His profile remains configured and fails closed until reauthenticated, with no
credential copying or synthetic readiness. Deployment/live results are reported
separately after actual CI, merge, backup and runtime verification; this pre-merge
evidence does not claim a deployment or an accepted product WP.

Current main protection was read live: projectctl + ci-gate required, enforce_admins
true. CHG-018 zero human development approvals is preserved. Product HITL unchanged.
