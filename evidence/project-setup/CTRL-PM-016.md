# CTRL-PM-016 — Plane metadata HTML wrapper compatibility

CONTROL ITEM: CTRL-PM-016
GOAL: Accept the installed Plane editor PRE/CODE representation while preserving strict JSON and canonical semantic comparison.
RESULT: Parser compatibility and read-only live audit PASS; new-current-head human review remains required before any merge.

## Root cause and scope

Preflight branch setup/project-management-bootstrap, local/PR HEAD c3aeca335a95adfac4ebb5a5d694b91da2f0e015. The only existing local change was the append-only failed merge diagnostic in CTRL-PM-015.md; it is retained in this scoped commit. Current genuine Ejlonn approval applies to that old head; it cannot certify this subsequent code change. PR2 stays open and unmerged.

Metadata path: plane_import._MetadataHTML → canonical_metadata → check_issue. WP-VALID-001 has one PRE with a direct CODE child, while the former parser rejected every start tag within PRE. Diagnostic comparison established unchanged JSON semantics; no Plane data corruption or canonical-doc repair is claimed.

The HTML parser now permits one optional direct CODE child with only whitespace before/after it. It rejects nested/repeated CODE, mixed payloads, unexpected child/closing tags, missing CODE/PRE closures, comments/declarations/processing instructions inside the metadata block and multiple metadata blocks. HTMLParser's existing convert_charrefs=True decodes entities once. Existing plain JSON in PRE and outer HTML envelope handling remain supported. An explicit raw JSON-object path fulfills the requested raw-input regression case without HTML stripping; it uses the same JSON decoder/object validation and does not decode HTML entities in raw JSON. No arbitrary HTML-to-text normalization or malformed JSON repair.

Existing json.loads duplicate-key rejection, dictionary-shape validation, identity checks and exact expected metadata comparison in check_issue are preserved. Semantic-drift regression invokes check_issue rather than certifying parser output alone. Import initialization policy is unchanged; live audit explicitly binds Batuhan's separately human-approved post-import assignment when constructing expected assignees, rather than replaying the old initialization allocation or changing canonical metadata.

## Executed verification

Before edits: full146tests passed in62.89s; projectctl validatePASS; git diff --checkPASS. Preflight read-only live audit confirmed only WP-VALID-001 wrapper rejection; identities, owners, states, counts and approved assignments passed independently.

Final focused test_plane_import.py:49passed in19.80s. Final full suite:170passed in67.75s. Added24cases cover raw JSON, legacy PRE/envelope, PRE/CODE, editor attributes, escaped Unicode/special characters with single decoding, malformed JSON, duplicate keys, non-dict JSON, multiple blocks, nesting/extra markup, missing closures, mixed payloads and successful parsing followed by semantic rejection through check_issue. projectctl validatePASS with947preserved warnings and execution UNAVAILABLE(documentation only). No warning suppression or validator weakening.

Fresh APIv1 live audit:11GETrequests only; exact audit equality before/after. All179 work items passed canonical_metadata and check_issue with regenerated expected canonical metadata and approved owner assignments. WP-VALID-001 passes the real parser path without any Plane rewrite. All179unique/allBACKLOG,0duplicates;Asrın73/Batuhan32/Selman0/Yavuz0,105assigned/74unassigned;canonical owners73/17/32/57;29modules/13cycles/10labels. Workflow, memberships and all audit-visible fields unchanged. No Plane mutation or product WP transition.

Final diff hygiene and canonical docs/AGENTS equality checked before commit. Only parser, focused tests, this report and necessary CTRL-PM-015 diagnostic/fix evidence are included. No reconciliation change, dummy user, product implementation, secret or new infrastructure.

FILES CHANGED: tools/projectctl/src/projectctl/plane_import.py; tools/projectctl/tests/test_plane_import.py; evidence/project-setup/CTRL-PM-016.md; evidence/project-setup/CTRL-PM-015.md.
PLANE READS: GET-only preflight and fresh final APIv1 audit.
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: Authorized setup checkpoint push; actual new head and CI results are verified at handback. No review/approval/merge by agent.
NETWORK MUTATIONS: GitHub push only; Plane GETs only.
KNOWN LIMITATIONS: CTRL-PM-011 remainsPARTIAL with Selman/Yavuz onboarding pending; CTRL-PM-015 remainsPARTIAL pending renewed review, actual merge/post-merge validation and previously documented pilot-representation limitations. Existing private-plan protection limitation remains. This is not SETUP COMPLETE.
SPEC CONFLICTS: NONE newly discovered or repaired.
COMMIT SHA: Resolve the atomic [CTRL-PM-016] commit containing this report; new exact HEAD is reported after push.
NEXT CONTROL ITEM: HUMAN_REVIEW_REQUIRED_AFTER_PARSER_FIX — Ejlonn manually reviews and approves the new exact PR2 HEAD. No merge is authorized in this increment, even if a review arrives during execution.
