# CHG-033 recovery proof: offline verification (2026-10-25)

Offline fixtures only; nothing ran against real Plane or GitHub, and nothing was installed. `results.json` holds each command, UTC start, exit code and result line; `run-manifest.json` binds the source hashes (base `HEAD` is the branch head before this change). The proof frees the implementation slot only; it is not DoD, acceptance or DONE evidence.

| Check | Result |
|---|---|
| plane-transition tests (226 existing + 9 new in `test_recovery.py`) | exit 0 |
| plane-queue tests | exit 0 |
| Ruff check and format, Pyright on `auto_next.py`, `reconcile.py`, `test_recovery.py` | exit 0, no findings |
| static ratchet, test strategy, flake policy, projectctl validate, catalog-lint with base | exit 0 |
| policy dry run with the real builder (new `deferred_recovery` block validated against real contexts) | exit 0 |
| `mutation_check.py` (24 injected defects in `recovery_proof`, scratch copy) | 24 caught, 0 survived (`mutation-check.txt`) |

Limits: one fixture-style real-adapter test (mocked `gh` transport) covers cache freshness and main/merge/PR binding; the live GitHub schema was not exercised. Installing the reviewed source, the owner re-assertion comment and the live proof evaluation are separate gated steps and have not happened.
