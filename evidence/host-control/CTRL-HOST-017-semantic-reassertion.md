# CTRL-HOST-017 — semantic identity for enriched merged-binding reassertions

CHG-036 is a C3 / CR-3 fail-closed correction to CHG-034. The original
VERIFIED `WAITING_EXTERNAL_INTEGRATION_BINDINGS` blocker audit remains the sole
active authority and is not edited. A later `UNCHANGED` `VALIDATING + BLOCKED`
row may add reviewed CHG-035 provenance detail to its reason when it keeps the
same wait class and exact `active_blocker_audit_id`.

The merged-binding proof still requires an unedited owner assessment at current
main, exact `External bindings` equal to the consumer registry IDs, matching
audited blocker fields, current pinned registry bytes and provenance, absent
future artifact paths, merged PR and exact green CI. UNKNOWN, local actionable
work, a changed blocker or class, missing or mismatched registry IDs/provenance,
or delivered paths remains rejected.

Focused regression coverage proves that enriched CHG-035 reason text passes only
with the same semantic wait class and binding proof, while the generic
reassertion default remains byte-identical for existing CHG-022/CHG-024 paths.
