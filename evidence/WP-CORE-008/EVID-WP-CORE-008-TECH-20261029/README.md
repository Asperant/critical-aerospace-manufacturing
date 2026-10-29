# EVID-WP-CORE-008-TECH-20261029

This directory is the immutable-by-commit technical EvidenceBundle referenced
by the WP-CORE-008 RTM rows. `manifest.json` hashes the focused real-runtime
scenario/checker outputs and the existing real runtime/browser/dispatch records.

The bundle is deliberately `TECHNICAL_EVIDENCE_PENDING_ACCOUNTABLE_ACCEPTANCE`.
It does not assert `VERIFIED`, final EV-L5 evaluation, full AV-SCEN coverage,
production security acceptance, or WP-CORE-008 `DONE`.

Provenance is explicit in `manifest.json`: `source_main_sha` is the historical
main revision used for the runtime execution (`ee060997b611fae16d6c4f13c0d85cebafaf17e7`),
while `technical_closure_merge_sha` identifies PR #210 and
`current_main_sha_at_refresh` identifies the current GitHub `main` revision
(`6299ab02491a9b7336b3637334ed461ce510ec21`). These fields must not be
collapsed into one SHA.
