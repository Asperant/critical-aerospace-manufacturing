# Vize demo runbook

This runbook covers the deliberately narrow, real demo slice: Core command →
PostgreSQL transaction/outbox → NATS JetStream → Twin projection → BFF →
Keycloak-authenticated browser/UI. It is a research/demo runtime, not a
production manufacturing or security acceptance environment.

## Before presentation

From the repository root:

```bash
./tools/demo-runtime/demo.sh reset
./tools/demo-runtime/demo.sh start
./tools/demo-runtime/demo.sh preflight
```

The demo uses its own Compose project (`cap-demo`) and state directory
(`~/.local/state/cap-demo` by default). The generated demo account is:

```text
username: demo.operator
password: read from ~/.local/state/cap-demo/credentials.env
```

Do not put that password in slides, commits, or evidence.

The scenario command uses the repository's Playwright installation when host
Node is available. On this shared host it automatically uses the pinned
`mcr.microsoft.com/playwright:v1.64.0-noble` container instead; npm packages
are installed only inside that disposable container, and the repository is
not modified by the browser step.

The demo browser spec is intentionally excluded from the generic CI harness;
the dedicated demo config is the authoritative runner for this isolated live
runtime.

## Live demo

1. Open `http://localhost:29090/overview`.
2. Click **Sign in** and authenticate in the real Keycloak page as
   `demo.operator`.
3. Enter `DEMO-WORLD` in **World ID** and select **Load overview**.
4. Point out the initial seeded lot (`DEMO-LOT-001`) and its normal state.
5. In a terminal run:

   ```bash
   ./tools/demo-runtime/demo.sh scenario
   ```

6. Refresh/load `DEMO-WORLD` in the browser. Point at `DEMO-LOT-001`,
   `HELD`, `ACTIVE`, `freshness FRESH`, and the quality-excursion reason.
7. Run the compact evidence check if requested:

   ```bash
   ./tools/demo-runtime/demo.sh verify
   ```

The scenario uses the real Core HTTP command path. It does not update a hold
row directly. Core acceptance returns `effect_verification=NOT_VERIFIED`; the
subsequent published outbox row, JetStream delivery, Twin ledger/projection,
BFF response, and browser result are the downstream evidence.
The generated evidence records the source revision used by the rehearsal; keep
that revision alongside the run identifiers when presenting or archiving it.

## What to point at

| Visible fact | What it proves |
|---|---|
| `DEMO-WORLD` | Explicit world scope is carried through the demo |
| `DEMO-LOT-001` → `HELD` / `ACTIVE` | Core state was changed by the command |
| `FRESH` and Twin source | The UI is showing a rebuildable Twin projection |
| quality-excursion text | The hold reason is understandable to a presenter |
| `latest.json` identifiers | Command, outcome, outbox and EventID can be traced |

## If something fails

Run:

```bash
./tools/demo-runtime/demo.sh preflight
./tools/demo-runtime/demo.sh status
```

For a clean retry:

```bash
./tools/demo-runtime/demo.sh reset
./tools/demo-runtime/demo.sh start
./tools/demo-runtime/demo.sh scenario
```

If the browser step is the only failure, inspect the Playwright output and
`evidence/demo-presentation/browser-result.json`. Do not claim browser success
unless `demo.sh verify` reports `OVERALL PASS`.

## After demo

```bash
./tools/demo-runtime/demo.sh stop
```

`stop` retains the isolated volumes for quick restart. Use `reset` before the
next clean rehearsal; it affects only the `cap-demo` project.
