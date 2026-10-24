# WP-SEC-003 slice 2: Core authorization enforcement mechanism

Status: IMPLEMENTED at unit level on branch `wp/WP-SEC-003-authz-policy`, on top of slice 1
(`4eb23ef59db5f2ecbb39919034615dc47a6c9e48`). Accountable owner: Asrın Dündar. This is
not API, integration or scenario acceptance, and it certifies no readiness.

## Delivered

- `services/manufacturing-core/src/manufacturing_core/enforcement.py`
  - `authorize(permissions, action)` returns only on ALLOW; otherwise it raises
    `AuthorizationDenied` (a `PermissionError`; the message carries no action text and no
    permission). A fault while evaluating is a denial.
  - `enforce(permissions, action, handler, *args, **kwargs)` authorizes first and calls the
    handler exactly once; on DENY the handler is never called.
  - `EnforcementRegistry.bind(action)` decorates a handler (the guarded callable takes the
    permissions first), rejects unknown and duplicate actions, and records the bound handler.
    `unbound_actions()` and `assert_fully_bound()` report catalogued protected actions without
    a binding.
- `services/manufacturing-core/tests/test_authz_enforcement.py` (TEST-SEC-003-001 with
  `test_authz.py`), local test handlers only.
- `services/manufacturing-core/README.md` section, docs/03 §19.7 and the FR-SEC-003 coverage
  row (EVIDENCE_PENDING), docs/04 repository reference.

## Checks run (development host, Python 3.11 CI toolchain)

- Focused Core unit tests (`test_authz.py`, `test_authz_enforcement.py`): 163 passed.
- `ruff check`, `ruff format --check` on the changed files; `pyright` for
  `services/manufacturing-core`: 0 errors.
- `ci/scripts/check_test_strategy.py`: PASS (83 test files, 0 violations).
- `projectctl validate`: exit 0 (existing warnings only). `git diff --check`: clean.
- Mutation sanity: handler called before authorization (61 tests fail), an evaluation fault
  that allows (1 fails), unbound detection disabled (4 fail); original restored, all pass.
- Not run: CI workflow, broad suites, integration, scenarios, benchmarks.

## Scope check: owner-executable implementation work remaining: NO

Everything left needs a surface that does not exist or an external producer:

- Binding to real Core command handlers: none exists. Hold/release handlers belong to
  WP-CORE-002 and the command acceptance pipeline to WP-CORE-003 (both Asrın, BACKLOG); each
  binds with `EnforcementRegistry.bind`. This slice invents no handler.
- Automation enforcement: no automation service exists; WP-AUTO-004 (Batu, BACKLOG) owns the
  ActionCatalog and authorization gate.
- Role-to-permission mapping: the exact RBAC matrix is an open question (docs/01) and the
  AuthorityPolicy artifact belongs to WP-HITL-001. Not implemented; unknown input stays DENY.
- API-level UI-bypass tests and the integrated TEST-SEC-AUTHZ-NEG: no command API exists, and
  the boundary is REAL/INTEGRATION.
- AV-SCEN-04, BENCH-RQ3-001, DOD-WP-08/09/11 evidence at the required boundary and identity
  binding: need the real integrated path.

External blockers named by the WP's own edges: DEP-016 (DN-RT-IDP at INTEGRATION_READY,
Yavuz; producers WP-SEC-001 and WP-HITL-004) and DEP-017 (DN-PLAT-CD at INTEGRATION_READY for
MILESTONE_EXIT, Yavuz; producers WP-CICD-002/003). Neither is certified.

## Not claimed

No fixture is milestone or final evidence. Nothing here claims AV-SCEN-04, BENCH-RQ3-001,
API or integration acceptance, DN-SEC-BASE readiness or DONE. Merged is not Done.
