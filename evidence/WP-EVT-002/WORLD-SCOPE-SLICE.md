# WP-EVT-002 — consumer-side WorldID scope validation

Accountable owner: Asrın Dündar (Asperant), authorized development session.
Branch: wp/WP-EVT-002-typed-envelope. Base:
`82d108ce844dc501c7ee876def836b6dcd624abf`. Evidence revision is this file's
containing commit. This is isolated library evidence, not WP acceptance or DONE.

The pure exported `validate_world_scope(envelope, expected_world_id)` returns the
same EventEnvelope object on an exact match. It rejects missing/null, blank or
non-string expected scope and mismatched scope, reusing the existing nonblank
identity validation. No trimming, coercion, case folding, Unicode normalization
or default world is introduced. Existing construction/decoding continues to reject
missing/malformed envelope WorldID. Errors contain field names and fixed failure
text, never supplied world values. Neither success nor failure mutates metadata.

This implements a bounded FR-EVT-004/ARCH-WORLD-SCOPE primitive under the WBS
WorldID validation deliverable and 02 INT-INV-06 consumer-context obligation.
It does not authenticate/authorize a world or prove real consumer isolation.

Run label: RUN-EVT-002-WORLD-SCOPE-LOCAL-001 (engineering label only).
Pinned `uv run --project ci --locked` toolchain:

- `pytest -c ci/pyproject.toml ci/tests/test_event_envelope.py -q`:
  **181 passed in 0.63s**, including 25 new scope cases. Asset TEST-EVT-002-001,
  TEST-EVT-ENVELOPE family, isolated unit/fixture boundary. Checks matching and
  mismatched worlds, missing/malformed expected world, existing malformed/missing
  envelope rejection, unchanged object/serialization, exact deterministic
  case/whitespace/Unicode comparison, and redacted errors.
- Changed envelope module, package exports and focused tests: Pyright
  **0 errors, 0 warnings, 0 informations**; Ruff lint/format and diff hygiene pass.

No broad/full suite, runtime integration or scenario was run. Schema, fixtures and
existing contracts are unchanged. No HTTP/NATS/Temporal propagation, outbox,
event producer, runtime consumer adapter, ACL, PR or lifecycle mutation is included.
Actual bindings, downstream adoption, REAL propagation/isolation/time evidence,
trace reconciliation and post-merge validation remain outstanding. No canonical
scope/architecture conflict was found for this exact-match library guard.
