# Team workflow — CTRL-PM-011

Status: PARTIAL — PENDING_EXTERNAL_INVITE_ACCEPTANCE. Human-provided identities are verified; external acceptance and individual authentication remain pending.

Use one persistent Ubuntu GUI session, `ailab`, with RustDesk attached. Do not create GUI users or switch Ubuntu login sessions. `/srv/ailab/project` is the integration/reference clone and must not be used concurrently for developer work.

| Developer | GitHub | Repository-local commit email | Workspace | Profile |
|---|---|---|---|---|
| Asrın Dündar | Asperant | asrindundar14@hotmail.com (existing verified identity) | /srv/ailab/workspaces/asrin/project | /srv/ailab/user-profiles/asrin |
| Selman Özdemir | selorito | selmanozdemir430@gmail.com | /srv/ailab/workspaces/selman/project | /srv/ailab/user-profiles/selman |
| Batuhan Kaya | eilonn | batuhankaya0204@gmail.com | /srv/ailab/workspaces/batuhan/project | /srv/ailab/user-profiles/batuhan |
| Yavuz Gümüş | Yavuzgmus | yavuzzgumus@gmail.com | /srv/ailab/workspaces/yavuz/project | /srv/ailab/user-profiles/yavuz |

Yavuz’s current operational identity is **Yavuz Gümüş**, Plane email **yavuzzgumus@gmail.com**, GitHub **Yavuzgmus**, and Git commit email **yavuzzgumus@gmail.com**. The corrected MEMBER invitation is pending acceptance; the earlier wrong-address invitation has been revoked. Historical invitation/workspace snapshots retain their original observations.

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
