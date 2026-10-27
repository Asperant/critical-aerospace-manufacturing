# TEST-CORE-LIFECYCLE

This runbook verifies the WP-CORE-009 state representation without asserting
transition legality. Legal transition semantics remain owned by WP-CORE-002.

## Focused local verification

Run from repository root:

```bash
uv run --project ci --locked python -m pytest \
  -c services/manufacturing-core/pyproject.toml \
  services/manufacturing-core/tests -m 'not integration' -q
uv run --project ci --locked pyright \
  --project services/manufacturing-core/pyrightconfig.json
uv run --project ci --locked ruff check services/manufacturing-core
uv run --project ci --locked ruff format --check services/manufacturing-core
```

The lifecycle test covers canonical order, lot, and serialized-component
lifecycle values; independent lot/component execution state; immutable
identity/revision and state records; stable JSON serialization; rejection of
unknown values; and the absence of a transition API.

## PostgreSQL verification

The real PostgreSQL fixture applies the forward-only `0003_lifecycle`
migration, verifies the three lifecycle-state tables and runtime grants, and
round-trips the state records through `CoreRepository.get_state`. It must be
run only with an explicitly disposable PostgreSQL 18 fixture:

```bash
CORE_TEST_DISPOSABLE=1 CI_PG_DSN='<disposable-admin-dsn>' \
  uv run --project ci --locked python -m pytest \
  -c services/manufacturing-core/pyproject.toml \
  services/manufacturing-core/tests/persistence -m integration -q
```

Local PostgreSQL execution is not claimed by this repository evidence until
that command completes. Required CI integration evidence is bound to the
implementation PR and its exact post-merge main revision.
