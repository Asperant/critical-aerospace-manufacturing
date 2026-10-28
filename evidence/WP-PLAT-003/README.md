# WP-PLAT-003 — Runtime service bring-up on the shared host: evidence

Owner: Yavuz Gümüş · supporting reviewer: Batuhan (advisory, CHG-018) · F1 · M2/S3–S4 ·
readiness node DN-PLAT-INTEG · requirements FR-PLAT-001, NFR-DEP-001.

DoR: owner assessment on issue #162 (started under CHG-054, `projectctl startability
WP-PLAT-003` = STARTABLE).

## Slices

| Slice | Content |
|---|---|
| 1 | Temporal 1.32.1 on the platform PostgreSQL (`temporal-schema` one-shot, `temporal`, `temporal-namespace` readiness probe), profiles planning/platform/full/e2e |
| 2 | Qdrant v1.19.2 with a per-host API key; MLflow 3.16.1 (metadata in PostgreSQL, artifacts in SeaweedFS) with an init job that alone holds the S3 admin identity and a bucket-scoped `cap-mlflow` identity for the server |
| 3 | 02 Sequence I startup order as static checks (layers, wait cycles, with negative graphs) and Keycloak health tolerance for its first boot |
| 4 | `cap-platform` realm imported as code with a service-account client; REAL token and wrong-secret tests |
| 5 | `readiness.json`: every runtime edge out of DN-PLAT-INTEG in 05, checked against 05 by tests; `stack.sh readiness` |
| 6 | RUN-PLAT-003-DEV-001, trace (03 §17, §19.11, delta) and this README |

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `infra/compose/tests/test_definitions.py` (TEST-PLAT-003-001) | TEST-PLAT-COMPOSE | static | CI t1-unit |
| `infra/compose/tests/test_runtime_integration.py` (TEST-PLAT-003-002) | TEST-PLAT-COMPOSE | REAL containers | CI t1-integration on the `full` profile; `stack.sh smoke` |
| RUN-PLAT-003-DEV-001 | TEST-DEP-PLATFORM, BENCH-DEP-STARTUP instrumentation | REAL | shared host (DEV) |

CI (run on the slice heads): t1-integration started the `full` profile and passed the REAL
tests in 32 s with images cached; on the shared host the same tests are 20 REAL tests
(`smoke.log.txt`). Locally at the final head: 72 static tests, the REAL suite, the static
ratchet, `projectctl validate` and the trace lint.

## Development run RUN-PLAT-003-DEV-001

Produced by `collect_run.py` on the shared host from a detached worktree at the revision in
`RUN-PLAT-003-DEV-001/record.json` (`a949c84`; the branch name is empty because of the
worktree). It starts the observability stack, resets, starts the `full` profile from empty
volumes with images local, runs the REAL tests and the readiness view, repeats `up`
(idempotence), simulates a reboot, runs readiness and the REAL tests again, restarts with data.
Credentials, host paths and the host name are placeholders.

| Step | Result |
|---|---|
| fresh start, empty volumes, images local | healthy in **283 s** (NFR-DEP-002's threshold is 600 s; measured on the loaded shared host, not the EVALUATION HardwareProfile) |
| REAL tests | 20 passed |
| readiness checklist | 10 of 10 edges OK (DEP-011 through the observability probes) |
| second `up` | idempotent; healthy in 51 s |
| restart with data | healthy in 246 s |
| memory against limits | Keycloak 735/1024 MiB, **MLflow 676/768 MiB (88 %)**, others well below; the nine platform containers together used about 1.84 GiB at that moment |
| **simulated reboot** | **not all healthy within the 926 s bound** (exit 1), see below |

### The reboot step did not pass

The step stops the platform and starts all nine long-running containers at once, without
Compose ordering, as Docker does after a reboot. In the recorded run PostgreSQL was `unhealthy`,
Temporal and its namespace probe had restarted 29 times and MLflow 6 times at 926 s, so the
readiness view showed only 6 of 10 edges OK. Immediately afterwards the REAL tests passed (20
passed in 3.8 s), so the services were working while Docker's health state lagged.

| Observation | Result |
|---|---|
| ad hoc check during development | all nine healthy after 121 s |
| diagnostic reproduction (`reboot-reproduction/timeline.log.txt`, not a RUN) | all healthy after 320 s; PostgreSQL showed `unhealthy` for about 4 of those minutes |
| recorded run | not all healthy after 926 s |

PostgreSQL logs a crash recovery after the stop; MLflow exits with "the database system is
starting up" and is restarted by Docker; Temporal restarts until its store answers. The host was
loaded (load about 6 of 8 CPUs, with my parallel test runs) during the reproduction. **The root
cause under load is not established**: I did not change the PostgreSQL health check or the restart
behavior on a guess. NFR-REL-005 (reboot with intact volumes, healthy or known-degraded within 10
minutes) belongs to AV-SCEN-12 / RES-REBOOT-001 and is not claimed; the recorded 926 s is above
that threshold and the reproduction below it, on a loaded DEV host.

## Findings

- **A one-shot job makes `up --wait` fail even with exit 0.** The namespace job was first a
  job that exited; Compose `--wait` reported the profile unhealthy. It now stays up as a health
  probe.
- **Qdrant's image ships dash as `sh`.** The `/dev/tcp` health check failed until it ran under bash.
- **MLflow 3 starts a pool of job consumers (about 150 MiB each)** that exhausted the 768 MiB
  limit and killed request workers; server-side job execution is disabled (tracking support only).
- **SeaweedFS reads S3 identities only at start**, so `stack.sh up` restarts a running gateway
  when the identities file changed.
- **The first readiness view reported DEP-011 as WAIT** while the observability stack was up (it
  asked `docker compose ps` of a file that needs credentials to render). Fixed (`a949c84`), the
  faulty run discarded and recorded again; two earlier collector runs ended early (one stopped
  by me to fix that defect, one killed when the session closed) and left no evidence.

## Known limitations

- The reboot recovery above; MLflow runs at 88 % of its memory limit.
- Temporal and MLflow connect to PostgreSQL as the platform user `cap`; dedicated least-privilege
  roles belong to WP-SEC-002.
- The realm holds one service-account client; roles, users, BFF/UI OIDC clients and TLS are
  WP-SEC-001. DEP-010's "real login works" is shown at service level only.
- Application deployables are not composed yet; the mandatory Integration profile, BENCH-E2E-001,
  E2E-01, AV-SCEN-12 and INSP-DEP-HOST remain open. EvidenceState is EVIDENCE_PENDING and
  `observed` stays null.
