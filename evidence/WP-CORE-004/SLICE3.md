# WP-CORE-004 slice 3 — immutable split/merge temporal lineage model

Owner: Asrın Dündar (Asperant). Date: 24 October 2026.
Implementation revision: the commit containing this evidence, on
`wp/WP-CORE-004-temporal-genealogy`, starting from
`d82b74f2a8f75748b90d5179042152b731f6b35a`.

## Canonical basis and bounded implementation

This implements only the domain/model part of the canonical task "model
split/merge lineage relations", for FR-CORE-010/011 and WL-INV-01/02/03 / KG-INV-04.
01 Item 09 Lot Split/Merge and Item 25 Lot Split/Merge, Material Conservation and
Temporal Semantics require preserved source identities/memberships, permanent
links, distinct occurrence/effective/recording semantics and no overwritten
history. 02 Event Ordering explicitly rejects a facility-wide total order.
Existing approved scope/authority is unchanged; this is a C1 derived internal
implementation, not a public event/command contract or a new architecture.

`LotMembershipSnapshot` stores immutable world/lot/component references.
`LotLineageEvent` records a split (one source, multiple fresh successors) or
merge (multiple sources, one fresh successor), reason, source-event ID, opaque
record identity/revision and separate aware occurred_at/effective_from/recorded_at
values. Parent/child pairs retain their source event and timing context; serialized
component objects/identities are never cloned or reassigned by this value API.

`LotLineageHistory` declares explicit root membership snapshots and a complete
local ancestry closure. It rejects missing parents, cycles, duplicate producers,
reused lot identities, double consumption, duplicate source-event/record IDs,
cross-world facts, and lost/invented/overlapping component membership. Original
roots/links remain available through later split/merge generations. Roots bound
the supplied closure; they do not invent lot creation events or birth timestamps.

Causal order comes from the lot relationships, not event IDs, opaque revisions,
receipt order or a global counter. Dependent facts cannot occur or become effective
before their producer ancestry, comparing actual UTC instants (including repeated
local hours). Equal times are allowed when explicit ancestry orders them.
Independent events may share times. Recording time is retained without being used
as occurrence/effectivity or compared across clock semantics. Complete input may
arrive out of order; validation follows ancestry but preserves the supplied tuple.
`append()` returns a new validated value without editing old links or snapshots.

These are internal representations of already-governed facts, not SplitLot/MergeLots
execution, merge-policy eligibility, current-state authority or a consumer replay
policy. Complete history cannot contain duplicate facts; transport idempotency,
source sequence/gap handling and envelope/simulation-clock bindings remain at
their canonical integration boundaries. No simulation-time conversion, expiring
membership interval engine, persistence, repository, schema or query endpoint was
added. Existing rework models and persistence are unchanged.

## Focused checks actually executed

Existing pinned `ci/.venv`, Python 3.11.16. Synthetic model fixtures only; no
database, broker, platform, external runtime or manufacturing execution was used.

| Command | Actual result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/test_lineage.py -q` | 38 passed in 0.11 s |
| `ci/.venv/bin/ruff check services/manufacturing-core/src/manufacturing_core/lineage.py services/manufacturing-core/tests/test_lineage.py` | All checks passed |
| `ci/.venv/bin/ruff format --check services/manufacturing-core/src/manufacturing_core/lineage.py services/manufacturing-core/tests/test_lineage.py` | 2 files already formatted |
| `ci/.venv/bin/pyright --project services/manufacturing-core/pyrightconfig.json --pythonpath ci/.venv/bin/python` | 0 errors, 0 warnings |
| `projectctl validate --json` after the two scoped RTM reference updates | PASS; 634 existing canonical diagnostics, zero errors |
| `git diff --check` | PASS |

Coverage includes valid splits/merges, four-generation ancestry with shared-root
merges and reversed delivery order, retained historical links/JSON round trips,
immutable nested membership/events, occurrence/effective versus recording time,
independent equal timestamps, causally ordered ties, backwards instant ordering
including a daylight-saving fold, invalid cardinality, ambiguous/duplicate IDs,
double consumption, missing ancestors, cycles, component conservation/cloning
and world isolation. Only this focused TEST-CORE-GENEALOGY model subset ran; no
broad/full test suite or whole-WP verification is claimed.

## Trace and remaining work

FR-CORE-010/011 REALIZED_BY reference the actual internal model. Coverage remains
ALLOCATED and final accepted evidence NOT_YET_EXECUTED while persistence and the
promised query/consumer boundary remain pending. No accepted EvidenceID is invented.
The next slice can persist these lineage facts relationally with focused DB tests;
this slice performs none of that work. Exposure queries/scale checks and protected
producer/eligibility/lifecycle integration remain later work, with DEP-029 unchanged.
No blocker remains for this model slice. Plane/lifecycle, other WPs, deployment,
AUTO_NEXT and the two pre-existing untracked Asrın audit files were untouched.
