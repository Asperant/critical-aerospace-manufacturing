CONTROL ITEM: CTRL-PM-011
GOAL: Individual identities and separate-clone discipline.
RESULT: PARTIAL — PENDING_HUMAN_IDENTITY_DATA.
FILES CHANGED: project_control/TEAM_WORKFLOW.md; this report (uncommitted partial work).
TESTS RUN: Baseline full suite and canonical validation; see subsequent completed control reports for final hygiene checks.
TEST RESULTS: 129 baseline tests passed in 59.93s; canonical validation PASS. Identity acceptance remains pending.
VALIDATION RESULT: PASS; all canonical counts retained.
OBSERVED INVARIANTS: Canonical ownership 73/17/32/57. Existing CTRL-PM-010 verified one Plane member, 106 unassigned WPs.
PLANE READS: Prior committed observation only; fresh reads recorded in later controls.
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: NONE
KNOWN LIMITATIONS: Need actual invitation emails and GitHub usernames for Selman Özdemir, Batuhan Kaya and Yavuz Gümüş, plus confirmation of each developer's individual Git identity and clone. No accounts or identities invented. Independent CTRL-PM-012 onward work continues under the latest explicit user instruction.
SPEC CONFLICTS: Latest user instruction overrides master H4 whole-run stop for independent safe work only.
COMMIT SHA: NONE — incomplete item is not committed as complete.
NEXT CONTROL ITEM: CTRL-PM-012, independent workflow setup.

Final same-run observations: fresh full Plane audit and post-restart discovery still find one project/workspace member; GitHub collaborator API lists only Asperant (admin). Unknown teammate values remain unknown. Independent012,013,014 completed and final draftPR2/144-test CI passed. No invitations,collaborator changes,OS accounts or guessed identity assignments. This item remains PARTIAL,uncommitted.

## Final continuation checkpoint (supersedes the missing-identity limitation above)

CONTROL ITEM: CTRL-PM-011
GOAL: Apply owner-provided identities and prepare isolated development under one ailab GUI session.
RESULT: PARTIAL — PENDING_EXTERNAL_INVITE_ACCEPTANCE. Identity values are now supplied and verified; acceptance is not fabricated.
FILES CHANGED: TEAM_WORKFLOW.md; tools/operations/developer_workspace.py; tests/test_developer_workspace.py; this report; CTRL-PM-011-invitations.json; CTRL-PM-011-github.json; CTRL-PM-011-workspaces.json; CTRL-PM-011-plane-readback.json.
IDENTITIES: selorito (148006490, Selman Ozdemir), eilonn (109923358, eilon#3358), Yavuzgmus (149728130, Yavuz Gümüş). Exact human-supplied usernames resolve to User accounts; display names do not replace owner-provided bindings.
PLANE MUTATIONS: Three verified API v1 POST workspace invitations, each role MEMBER=15. Installed router/view/serializer and successful GET verified the contract. Each HTTP201 was freshly reconciled. No repeat POST, assignment, state change, member creation or deletion. Email-task delivery is not implemented in the inspected v1 create handler and delivery is not certified.
GITHUB MUTATIONS: Three developer collaborator invitations with permission push (write), read back as pending. No admin grants, owner access changes, review or merge.
HOST EFFECTS: Four independent local clones at integrated main6bb093c and four empty profile trees. Local identities and canonical HTTPS origin configured; no credentials copied or authentication performed. No Ubuntu users created. Original owner identity verified before clone preparation.
KNOWN LIMITATIONS: All three workspace invites and GitHub invites pending. Project membership requires a real active workspace account. Asrın remains73 assigned; other106 remain unassigned. Shared Linux user/profile isolation is operational, not a security boundary. Developers must authenticate/verify their own accounts and accept access.
SPEC CONFLICTS: Latest explicit single-session policy supersedes the earlier optional separate-Linux-user recommendation. Canonical documents untouched. No semantic conflict newly resolved.
COMMIT SHA: Resolve the checkpoint commit containing this appended section; it does not claim control completion.
NEXT CONTROL ITEM: Independent CTRL-PM-015 review preparation; external acceptance remains human-owned.

TESTS RUN: Two focused workspace safety tests; full146-test projectctl suite; validate/status; dedicated live Plane module/cycle/member/invitation readback; local clone identity/status/profile inspection; git diff --check; docs/AGENTS against main; secret scan before commit.
TEST RESULTS: 2 focused passed;146 passed in62.82s; validation/status PASS. Workspace readback confirms four clean clones and zero credential/profile files.
VALIDATION RESULT: PASS;947 warnings retained, execution UNAVAILABLE.
OBSERVED INVARIANTS:306/186FR/120NFR,179WPs/owners73–17–32–57,29areas,100nodes/217edges/208HARD/9SOFT/0cycles,174scheduled/exact5unscheduled,13cycles/9milestones. Live readback55GETs:179BACKLOG,29modules/179memberships,13cycles/174memberships,10labels,73assigned/106unassigned,zero duplicates.
PLANE READS: Paced GET-only preflight, invitation/member reconciliation and complete structural/membership readback.
NETWORK MUTATIONS: Three approved Plane invitation POSTs; three approved GitHub write-permission invitations. No other remote effect in this control checkpoint.

## Yavuz identity correction — current operational record

The latest explicit human correction supersedes Yavuz’s earlier email binding. Current identity: **Yavuz Gümüş**, Plane email **yavuzzgumus@gmail.com**, GitHub **Yavuzgmus**, Git commit email **yavuzzgumus@gmail.com**. Historical invitation and workspace JSON snapshots retain their actual observations; they are not current contact records.

Read-only preflight found exactly one pending wrong-address invitation aff3e366-a5ac-4168-b9ce-e1907f26a784, accepted=false/responded_at=null. Installed APIv1 WorkspaceInvitationsViewset.destroy checks those conditions server-side and scopes the target to the workspace. Under explicit scoped deletion authorization, only that invite was deleted (HTTP204), then its absence was verified. Exactly one MEMBER(role15) invite was created for the corrected email (HTTP201), IDd313768d-7a6d-4bc7-8a93-d9a8f40ac32b, pending and freshly reconciled. No blind retries or duplicates. Email-task delivery is not implemented in the inspected APIv1 create handler and is not certified.

Selman/Batuhan invitation records were compared before/after and remain identical. Full before/after project audit confirms work items, states, labels, modules, cycles and memberships unchanged:179 WPs,73 assigned/106 unassigned. No dummy users, WP assignments or workflow transitions.

Updated onboarding/helper identity and only Yavuz’s existing repository-local user.email; no global/integration/other-developer identity change. Exact verification is recorded in CTRL-PM-011-yavuz-identity-correction.json. Canonical docs/ and AGENTS.md remain untouched. Normal human acceptance/member verification remains required; invitation creation is not active membership or setup completion.


## Batuhan real membership repair — 2026-10-13

Latest owner instruction explicitly authorizes adding only Batuhan's verified existing account as normal workspace/project MEMBER, without WP assignments, workflow edits, other-team changes or PR merge. This checkpoint supersedes historical Batuhan-pending membership observations above, preserving them as historical evidence.

Read-only APIv1 audit found Batuhan already in the workspace and absent from CAP project membership; no live Batuhan workspace/project invitation exists. APIv1 has no global-user directory or workspace-member-create contract in this installation. Supplementary installed Django ORM queries were read-only and restricted to public identity/membership fields; no password, session, token or credential was inspected/output. Exactly one active non-bot account matches normalized email batuhankaya0204@gmail.com: user51137169-2989-42bd-9260-997b26e7e6dd, account-created2026-10-13T17:48:27.033958Z. Workspace membership407cf7e0-6cb2-4268-a400-ccfd79ee8d37 was created2026-10-13T17:48:35.471746Z by that user, active role15.

Historical invite3cb8faff-b07b-4af1-a614-20b842e875ed matches the exact email and was soft-deleted2026-10-13T17:48:35.508301Z; accepted=false/responded_at=null remain in the historical row. These flags are not proof of rejection or failed acceptance: installed UserWorkspaceInvitationsViewSet.create bulk-creates workspace membership then deletes joined invitations without updating these flags. API logs in17:48:20–17:48:45Z show recipient GET /api/users/me/workspaces/invitations/200 then POST to the same path204. Membership actor/timestamps and deleted invite reconcile with this normal authenticated flow; no acceptance was simulated by the agent. The recipient queryset filters exact email and uses the live soft-deletion manager; it does not exclude API-created invitations or require a user-FK/token for listing. Invitation model has no recipient-user FK. No normalization mismatch, duplicate account, new invitation or broken-invite replacement was needed.

Observed cause: D — workspace membership exists, separate project membership missing. Graduation Project/CAP is private (network0); installed ProjectViewSet filters a workspace MEMBER's project list to active project membership or public projects(network2). Thus the empty invites list reflects a consumed invitation; private CAP remained hidden because Batuhan was not a project member.

Installed APIv1 ProjectMemberListCreateAPIEndpoint.post + ProjectMemberSerializer accept member=userUUID and role15, validate existing workspace membership, derive workspace from the scoped project and default is_active=True. The API contract creates project user preferences as normal membership housekeeping; it does not assign WPs. Immediately before mutation, APIv1 members-lite confirmed exact email/userID/active/non-bot/workspace role15 and absence of project membership.

Exactly one POST /api/v1/workspaces/critical-aerospace-manufacturing/projects/beb6dbea-4931-4ce9-b761-a4957c4b33be/members/ with member51137169-2989-42bd-9260-997b26e7e6dd,role15 returned201; no retry. Fresh APIv1 project-members-lite and supplementary read-only ORM confirm one active MEMBER project membership9af8a17e-d285-4239-8f68-0c65c4e0c7f0. Workspace membership was already active and was not changed. No admin/owner grant, dummy user, new invitation, invitation deletion by this task, restart, credential sharing, canonical-doc edit or PR merge.

Full before/after APIv1 audits have exact equality for project, work items, states, labels, modules, cycles and workspace members. Project member delta is exactly Batuhan; all existing project members unchanged. Remaining Selman/Yavuz invitations are identical. Validation:179uniqueWPs,zero duplicates,allBACKLOG,73assigned/106unassigned,canonical owner metadata Asrın73/Selman17/Batuhan32/Yavuz57. Batuhan's32WPs were not assigned. Modules29/cycles13/labels10 unchanged.

Next browser action: refresh Plane at the canonical MagicDNS URL, select Critical Aerospace Manufacturing workspace and open Graduation Project/CAP. If the current client keeps a stale sidebar, sign out and sign back in with batuhankaya0204@gmail.com, then select that workspace/project. No invitation acceptance remains pending for Batuhan. Backend membership is active; a post-repair browser refresh is not independently witnessed.

PLANE MUTATIONS: one Batuhan project MEMBER creation only.
INVITATION MUTATIONS: NONE.
WP ASSIGNMENTS/WORKFLOW MUTATIONS: NONE.
GIT COMMIT/PUSH/PR MUTATIONS: NONE in this repair.

Repository checks for this repair:146projectctl tests passed in63.46s; projectctl validatePASS; git diff --checkPASS; docs/ and AGENTS.md unchanged fromHEAD. Only this append-only evidence file changed; no commit or push. Final backend status:BATUHAN_MEMBERSHIP_ACTIVE.


## Final Batuhan closure / identity correction — 2026-10-13

Control status: PARTIAL — Batuhan real identity, clone Git identity, membership and browser visibility verified; Selman/Yavuz onboarding pending. Historical eilonn/109923358 binding is WRONG for Batuhan and must not be reused. Current GitHub Ejlonn/143555644 is verified live as User with write permission. Prior wrong-account pending invitation337392232 was revoked under earlier explicit authorization; corrected invitation337567810 was accepted by the real account, with no live Batuhan GitHub invite remaining. Historical JSON snapshots are preserved and superseded by CTRL-PM-011-batuhan-closure.json; no old observation is rewritten.

Batuhan identity: Batuhan Kaya; Plane and Git commit email batuhankaya0204@gmail.com; Plane user51137169-2989-42bd-9260-997b26e7e6dd; GitHub Ejlonn. Live APIv1 members-lite confirms one active MEMBER(15) workspace/project identity, no bot/admin grant and no Batuhan stale invitation. Existing separate clone has local user.name Batuhan Kaya/user.email batuhankaya0204@gmail.com and clean working tree; no clone credentials were copied or inspected. Human personally confirms remote MagicDNS CAP project visibility.

Preflight PR2 open/non-draft/MERGEABLE at ee32f2c201b72f51c4e99782d868adbf214c2075, push+PR CI green. Ejlonn genuine COLLABORATOR APPROVED review at2026-10-13T18:03:03Z binds to that exact head. Preflight full146tests passed in64.02s, validationPASS and diff hygienePASS. No material conflict with supplied facts. A new identity/evidence commit is necessary, so that approval is not automatically valid for the new head. This checkpoint does not fabricate a fresh approval or certify merge.

Authorized owner-assignment preview compares all32targets to parsed canonical WBS ownership and embedded canonical metadata, BACKLOG and empty assignees. Exact source hashes and every WP/Plane ID are recorded in the closure JSON. One-shot preview helper initially used an incorrect Owner attribute, raised AttributeError before any mutation and was corrected to canonical_name; no canonical invariant or implementation/test was changed. All32PATCH calls update only assignees to Batuhan UUID, serialized through existing APIv1 RequestGate at >=1.25s with bounded Retry-After-aware handling and read-before/read-after verification. No ambiguous response or retry occurred. Full audit verifies precisely those32assignment deltas, no other work-item field, state, structure, membership or remaining invitation change. No destructive rollback, automatic READY or DONE.

Final live assignment result: Asrın73/Batuhan32/Selman0/Yavuz0;105assigned/74unassigned;179unique/allBACKLOG,zero duplicates;canonical owners73/17/32/57. Recomputed Batuhan assignment plan requires0mutations, all32correctly assigned. Selman GitHub invite remains pending and Plane invite remains pending; Yavuz GitHub write active but Plane invite remains pending. No teammate acceptance is manufactured. Later teammate activation/assignment requires a separate authorized verified-identity operation.

CTRL-PM-011 remains globally PARTIAL. Batuhan onboarding/assignment portion verified; review closure for the new correction HEAD remains human-owned. Product implementation, reconciliation merge/push, network policy changes and PR merge are not performed. Current operational metadata in TEAM_WORKFLOW/helper uses Ejlonn; old historical references remain explicitly superseded here.

Final correction checkpoint checks executed:146tests passed in63.20s; projectctl validatePASS with947preserved warnings; status execution UNAVAILABLE(documentation only); git diff --checkPASS; canonical docs unchanged frommain and AGENTS.md unchanged fromHEAD; tracked-path and changed-file API-key checksPASS. New current-head Ejlonn review is required after this commit/push. No merge/post-merge claim.


## Fresh activation observation after setup merge — 2026-10-13

Status remainsPARTIAL. Batuhan identity/member/32assignment and genuine reviewed setup closure verified; Asrın73assignments retained. During read-only post-merge audit, Yavuz independently appeared as active workspace MEMBER15, user3ccd9ad8-99e9-4b75-ae65-2325503d347f, exact corrected emailyavuzzgumus@gmail.com; pending Yavuz workspace invitation now absent. No Yavuz CAP project membership and0Yavuzassignments. Selman invitation still pending with no project membership/assignments. This supersedes historical all-three/then-two Plane invitation observations without rewriting history. No teammate membership or assignment was changed by this merge pass. See CTRL-PM-015-post-merge.json for fresh verified identity/count evidence.


## Yavuz onboarding / approved canonical assignment — 2026-10-13

RESULT: PARTIAL — Yavuz portion COMPLETE; Selman onboarding remains unfinished. Historical pending-Yavuz records above are retained observations, superseded by this fresh checkpoint. Latest explicit owner authorization permits exactly Yavuz's 57 canonical assignments; no Selman WP or membership change.

Fresh APIv1 workspace/project members-lite verifies exactly one active non-bot MEMBER(15) for yavuzzgumus@gmail.com, user 3ccd9ad8-99e9-4b75-ae65-2325503d347f; no pending Yavuz invitation. His existing CAP membership was added in the preceding explicitly requested access task, not this batch. GitHub binding remains Yavuzgmus; separate clone local user.name/user.email read back as Yavuz Gümüş/yavuzzgumus@gmail.com. No authentication/acceptance, new account, admin role or dummy identity is fabricated.

Preflight main feb255df0311d95e278369f04f2e22c0c971e70c equals fresh origin main, integration tree clean. PR2 freshly confirmed MERGED to that baseline. Existing control/evidence worktree 711c6cd contains valid historical post-merge evidence; its three files are preserved on this single batch branch without blindly cherry-picking or rewriting history. Reconciliation worktree untouched. Full preflight suite:170 passed in63.34s; validatePASS with947warnings retained; status executionUNAVAILABLE(documentation only).

The one-shot read-only preview initially referenced nonexistent WorkPackage.owner and failed before any mutation. It was corrected to primary_owner.canonical_name; no repository parser/model/test change or canonical repair occurred. Every preview target resolves to Yavuz in WBS and expected embedded metadata, is BACKLOG and unassigned. Exact 57 WP/Plane identities, source manifest, before/after audit hashes and each PATCH/readback result are in CTRL-PM-011-yavuz-closure.json.

Exactly57 serialized APIv1 PATCH requests set only assignees to that verified Yavuz UUID. Each target was freshly read before mutation and reconciled afterward through the existing >=1.25s, Retry-After/reset-aware RequestGate. All57 succeeded on first attempt; no ambiguous response or retry. Full fresh before/after comparison verifies precisely those57assignee deltas and no other item field, workflow, structure, membership or invitation change.

Final assignment result:Asrın73/Batuhan32/Yavuz57/Selman0;162assigned/17unassigned;179unique,allBACKLOG,0duplicates;canonical owner metadata73/17/32/57. Recomputed Yavuz assignment needs0mutations. Existing Selman invitation remains pending and no active Selman workspace/project membership exists. Product implementation and WP readiness/DONE are not authorized or asserted.

PLANE MUTATIONS:57 assignee-only PATCH requests; no membership/invitation/state/structure mutation in this batch.
SPEC GATE:CTRL-PM-015 pilot representation remains undefined; no pilot creation or completion claim. Final checks and evidence/PR disposition are recorded in the corresponding CTRL-PM-015 batch section.


## Control pilot preparation follow-up — 2026-10-13

Yavuz COMPLETE / Selman PENDING remains the current team truth. This follow-up adds a separate allowlisted control-only pilot owned by Asrın, without changing any canonical WP assignment or teammate membership/invitation. Canonical assignment totals remain73/0/32/57 (162assigned/17unassigned), excluding the control item. Historical711c6cd observations and the five prior closure files are preserved in the same batch branch; no duplicate historical report is created. See CTRL-PM-015-control-pilot.json for the separate pilot's live evidence.


Concurrent live observation during pilot preparation:Selman's real account a3d25336-e7d0-43f8-bfef-c0b5c2137a60 (exact emailselmanozdemir430@gmail.com, active non-bot MEMBER15) independently appeared in workspace members. Fresh project-members-lite contains no matching account and the previous workspace invitation is now absent. This is observed active membership, not an agent-created account or fabricated acceptance. No membership/invitation/assignment request forSelman was sent. His17WPs remainunassigned; CAPmembership/onboarding completion remains pending. The conservative snapshot equality check initially stopped on this single newly appearing workspace member; fresh targeted identity reads and a new full structural audit preserve/report that live truth without reverting it or forcing stale invitation counts.
