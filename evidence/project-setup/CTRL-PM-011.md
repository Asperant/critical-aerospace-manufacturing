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
