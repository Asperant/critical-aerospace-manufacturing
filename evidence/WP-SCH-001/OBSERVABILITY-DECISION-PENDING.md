# Observability applicability — decision pending (WP-SCH-001)

**Status: OPEN, owner Yavuz (platform owner, WP-OBS-001). No disposition exists.**
`infra/observability/coverage.json` is unchanged and lists `scheduler-service` as
`NOT_PRESENT`; origin/main (d2753de, fetched 2026-10-27T20:01Z) still does. The
manufacturing-simulator exemption (PR #75) does not cover this deployable.

Once `services/scheduler-service` exists, `cap_observability check-coverage` fails
(`NOT_PRESENT` is a violation for an existing deployable). Output of
`python -m cap_observability check-coverage infra/observability/coverage.json`,
2026-10-27T20:01:37Z, exit 1, verbatim:

    VIOLATION scheduler-service: exists at /srv/ailab/workspaces/batuhan/worktrees/WP-SCH-001/services/scheduler-service; declare logging ADOPTED or PENDING
    VIOLATION scheduler-service: exists at /srv/ailab/workspaces/batuhan/worktrees/WP-SCH-001/services/scheduler-service; declare health ADOPTED or PENDING
    telemetry coverage: 5/9 mandatory deployables exist; logging 0/5 adopted (4 pending); health 0/5 adopted (4 pending); 4 not yet present

The CI observability step therefore fails on this branch until the decision is made.
It is deliberately not silenced.

**Request to the platform owner.** The package is an offline library with no process,
endpoint or log sink (`services/scheduler-service/README.md`). Please either (a) confirm
an exemption with your own owner and expiry for `scheduler-service` (logging and
health `PENDING`, to be adopted with a scheduler service runtime), recorded in an
attributable PR, or (b) state another disposition (for example a different package
location, or adoption now). The terms to apply are yours; none are proposed here as
values. When a disposition exists, bind its exact terms in `coverage.json` and re-run
the check; the checker itself is not changed.

Until then WP-SCH-001 DOD-WP-06 is not claimed and the PR's required observability
check is expected to stay red.
