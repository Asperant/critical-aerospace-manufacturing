# WP-PLAT-001 — Compose profiles and mandatory runtime composition: evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın (advisory, CHG-018) · F0 · M1/S2 ·
readiness node DN-PLAT-COMPOSE · requirements FR-PLAT-001, FR-PLAT-002,
NFR-DEP-001, NFR-DEP-002, NFR-DEP-006.

DoR: owner assessment on issue #51 with DEP-003 producer readiness at
SKELETON_READY (READY verified 2026-10-24).

## Slices

| Slice | Content |
|---|---|
| 1 (`0c878e6`) | `infra/compose/compose.yaml` infra layer (PostgreSQL, NATS JetStream, Valkey, SeaweedFS, Keycloak) in all eight 02 profiles, `stack.sh`, static and REAL tests, CI steps, CODEOWNERS. Shared host: images pulled, all five healthy in 147 s on first start, 13 REAL tests passed |
| 2 | `infra/mfgctl/capabilities.json` (mfgctl.capabilities/v1 instance, DEP-003): eight profiles, `platform-infra` smoke through `stack.sh smoke`; credentials moved to Compose env files outside the repository so `mfgctl up` works without exported variables |

## Profile set

02 defines the minimum profiles `infra, core, vision, ai, planning, platform,
full, e2e`; the 04 card lists `core, vision, ai, automation, full`. The 02 set
is implemented: automation belongs to `planning` in 02, and Integration is an
environment class, not a runtime profile (02, Item 43 §7).
