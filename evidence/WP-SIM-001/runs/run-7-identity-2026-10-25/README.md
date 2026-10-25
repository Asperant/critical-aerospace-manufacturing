# run-7: new kernel run with execution identity (2026-10-25)

NEW local evidence from `capture_run.py` on the committed source in `identity.json` (commit `60c0359b`, clean tree, branch `wp/WP-SIM-001-owner-evidence-closeout`). It does not repair or relabel run-5: that run's Release, Environment, Hardware and exact-commit gaps stay UNAVAILABLE (see `DOD-WP-11-IDENTITY-ADDENDUM.md`).

| Command | Result | Output SHA-256 |
|---|---|---|
| simulator suite (`-p pytest_quarantine`, locked toolchain) | exit 0, `202 passed in 2.02s`, JUnit `test-results.xml` | `suite-output.txt` `ed587fdf…bd12` |
| `replay_comparison.py` | exit 0; fresh-process traces equal the in-process trace for all 6 seeds and 4 hash seeds | `replay-comparison.json` `e3291575…baec` |

Limits: toy-kernel scenario on the shared development host, not CI, INTEGRATION or EVALUATION. `identity.json` holds local labels (CPU model, memory, versions, source hashes), not a governed ReleaseManifest, EnvironmentManifest or Hardware ID, and a Git commit is not a release. DOD-WP-11 stays incomplete until those governed identities exist. No benchmark, container or REAL acceptance was run.
