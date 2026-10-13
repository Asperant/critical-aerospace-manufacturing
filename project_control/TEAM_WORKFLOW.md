# Team workflow — CTRL-PM-011

Status: CTRL-PM-011 COMPLETE — all four real team identities have active Plane workspace/CAP memberships, verified GitHub access, separate clean clones/profiles and repository-local Git identities. All 179 canonical WPs are assigned to their owners (73/17/32/57) and remain BACKLOG. CTRL-PM-015 remains IN_PROGRESS; its separate control-only pilot awaits the actual final closure PR, independent review, merge and post-merge validation.

Use one persistent Ubuntu GUI session, `ailab`, with RustDesk attached. Do not create GUI users or switch Ubuntu login sessions. `/srv/ailab/project` is the integration/reference clone and must not be used concurrently for developer work.

| Developer | GitHub | Repository-local commit email | Workspace | Profile |
|---|---|---|---|---|
| Asrın Dündar | Asperant | asrindundar14@hotmail.com (existing verified identity) | /srv/ailab/workspaces/asrin/project | /srv/ailab/user-profiles/asrin |
| Selman Özdemir | selorito | selmanozdemir430@gmail.com | /srv/ailab/workspaces/selman/project | /srv/ailab/user-profiles/selman |
| Batuhan Kaya | Ejlonn | batuhankaya0204@gmail.com | /srv/ailab/workspaces/batuhan/project | /srv/ailab/user-profiles/batuhan |
| Yavuz Gümüş | Yavuzgmus | yavuzzgumus@gmail.com | /srv/ailab/workspaces/yavuz/project | /srv/ailab/user-profiles/yavuz |

Yavuz’s current operational identity is **Yavuz Gümüş**, Plane email **yavuzzgumus@gmail.com**, GitHub **Yavuzgmus**, and Git commit email **yavuzzgumus@gmail.com**. His real Plane account `3ccd9ad8-99e9-4b75-ae65-2325503d347f` is an active workspace/CAP MEMBER (15), with all 57 canonical Yavuz WPs assigned and still BACKLOG. No pending Yavuz invitation remains. The earlier wrong-address invitation was revoked. Historical invitation/workspace snapshots retain their original observations; see the source-bound CTRL-PM-011-yavuz-closure evidence.

Batuhan’s current operational identity is **Batuhan Kaya**, Plane email and Git commit email **batuhankaya0204@gmail.com**, Plane user ID **51137169-2989-42bd-9260-997b26e7e6dd**, GitHub **Ejlonn**. The earlier `eilonn` binding was incorrect and identifies a different account; historical snapshots are retained as history. His workspace/project memberships are active MEMBER (15), and he personally confirmed remote CAP project visibility. His genuine approval on `ee32f2c` is historical once this correction is pushed; a new approval must bind to the new current HEAD.

All four independent clones were prepared from the integrated `main` baseline, with origin set to the canonical GitHub repository, repository-local names/emails and no copied credentials. They will need a normal fetch after individual authentication to receive setup updates. They are not authenticated merely because a clone exists.

## Onboarding

Replace `selman` with your own profile key (`asrin`, `selman`, `batuhan`, `yavuz`):

```sh
python /srv/ailab/project/tools/operations/developer_workspace.py shell selman
git config --local --get-regexp '^user\.'
gh auth login --hostname github.com --git-protocol https
gh api user --jq .login
```

Verify the returned account equals the table before any fetch/push/review. Accept your own GitHub invitation. Configure your own Codex/OpenAI account only within this profile; never copy integration-session credentials. Quit this shell when finished. Use the same launcher for every Git/GitHub command; a terminal outside it may inherit shared-session authentication.

```sh
python /srv/ailab/project/tools/operations/developer_workspace.py code selman
```

This opens VS Code with separate user-data and extension directories. Authenticate extensions individually and verify their account before use. The launcher separates GH_CONFIG_DIR, CODEX_HOME, XDG_CONFIG_HOME and VS Code data, disables global/system Git configuration and removes inherited GitHub/OpenAI/Plane token variables and SSH-agent references. Separate profile directories in the same Linux account are operational isolation, not a security boundary against other processes running as `ailab` or a guarantee about extension/keyring behavior.

Log into Plane yourself using the supplied invitation email. API invitation records were created and read back; email delivery was not proven. If no invitation is visible after login, ask the workspace owner to use Plane's normal invitation UI; do not fabricate membership or copy invitation tokens. After workspace acceptance, an owner must verify active membership and add the real account to Graduation Project/CAP with MEMBER permission. WPs stay unassigned until project membership resolves. Repository invitation acceptance is also personal.

After authentication, fetch the remote normally, inspect its baseline, and use an existing local environment or install the documented projectctl dependencies in your own clone. Run `projectctl validate`, retrieve `projectctl context <WP-ID>`, check readiness, and create `wp/<WP-ID>-<short-slug>` only for an approved canonical WP. Product implementation has not been authorized by setup. Use `control/<CTRL-ID>-<short-slug>` for approved controls; the long-lived setup branch is the approved exception.

Canonical owners never change to compensate for missing accounts. No dummy users, substituted owners, shared tokens, global Git identity, automatic READY/DONE, self-approval or shared concurrent working tree. See ENGINEERING_WORKFLOW.md and canonical docs/08 for review and post-merge evidence rules.


Selman’s verified operational identity is **Selman Özdemir**, Plane/Git commit email **selmanozdemir430@gmail.com**, GitHub **selorito**, Plane user **a3d25336-e7d0-43f8-bfef-c0b5c2137a60**. Fresh API v1 reads confirm active workspace and CAP MEMBER (15), all 17 canonical Selman WPs assigned and BACKLOG, and no pending invitation. GitHub WRITE access is active. The account profile currently has first name Selman and an empty last name: these assignments bind the verified exact email/user UUID rather than guessing from display names. Historical pending observations remain preserved.
