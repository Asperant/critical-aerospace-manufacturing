# CTRL-DOC-006 — Citation, traceability and missing-artifact reconciliation

606 RTM catalog locations (306 View A and306 YAML metadata) now identify the exact stable requirement row/heading in01. Catalog Item81/82 range references and the unique Item16 Structured InspectionResult heading citation were repaired without fuzzy matching. The validator was unchanged. The baseline test now requires zero stale catalog citations; a new negative case corrupts one location and verifies exactly one warning for that same requirement. Full suite:145 passed; offline validation PASS; canonical semantic model unchanged. Remaining641 warnings are real missing metadata/readiness/precision/fallback/need-by findings.

A full canonical numeric-reference/link scan is recorded in the machine companion. Remaining references lacking a uniquely proven semantic target are retained for review; authority/evidence L0–L5 levels must not be misread as source-line citations. No claim that every line-only citation is verified. Planned companion/artifact names are not materialized by inventing content. The previously dangling DOMAIN_MIGRATION_CHANGELOG.md now exists as a reconstruction from current01/02 and actual Git baseline history, with no historical approval/date invention.

Item43: two raw occurrences have byte-identical stripped content; one logical item remains the02 R-001 interpretation. Neither duplicate is deleted. Stable legacy invariant/KPI/test IDs, external titles and migration comparisons remain intact.

Missing Requirement Revision/Status and120 structured NFR verification/evidence/context fields remain null/unspecified. RTM now makes that source-gap interpretation explicit; no owner, threshold, revision, EvidenceID or executed status is fabricated. Original planning evidence and source hashes remain historical.

Inspection conflict:01 Item16 describes conceptual possible fields and later schema finalization, while02 labels a projection mandatory/canonical. The source citation now reaches the actual heading, but the semantic labels remain unchanged pending INSPECTION_CONTRACT_CANONICALIZATION and review of later Item22 refinements. Citation repair does not approve a schema.

09's original empty-registry snapshot remains historical, with an additive pointer to the16 current records, all UNDER_REVIEW. Local branch application does not constitute independent peer approval, merge, VERIFIED/CLOSED change status, release acceptance or WP completion. No Plane/GitHub/network mutation.
