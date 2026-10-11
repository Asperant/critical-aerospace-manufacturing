Offline project tooling for **CTRL-PM-001…005**, control items outside the 179 canonical WPs.

With the declared dependencies already available locally:

```sh
python -m pip install --no-index --no-build-isolation -e 'tools/projectctl[test]'
projectctl parse
projectctl validate
projectctl status
projectctl context WP-CORE-001
projectctl next --owner Batu --cycle S2
python -B -m pytest tools/projectctl/tests
```

Alternatively, set `PYTHONPATH=tools/projectctl/src` and run `python -B -m projectctl`.
The CLI discovers the repository from the current directory or accepts `--root`.
`parse` emits JSON; `validate` and `status` also support `--json`.
Commands emit to stdout, never save generated state, and use no network clients.

Validation covers WBS, schedule/roadmap agreement, dependency topology and registry
mirrors, canonical requirements and RTM metadata. Architecture references remain
source assertions; existence against the 02 registry is not yet checked.
Semantic findings are WARNING diagnostics for offline inspection, never permission
to satisfy a dependency or certify readiness. Structural/identity/conflicting
metadata errors fail validation. No known-finding suppression or documentation
repair is performed. Requirement revision/status and NFR metadata gaps stay null.

`parse` emits the unified model, source hashes and parser version. `context` shows
canonical WP data, all cycle memberships and relevant unresolved findings. `next`
lists mandatory scheduled planning candidates, without knowledge of execution
state or any readiness certification. No optional/unscheduled work is selected.
Raw expectations and source spans are preserved; lines are locations, not identity.
Raw `NOT_STARTED` never becomes execution state. No sync, READY or DONE operation
exists. All default commands write only to stdout and require no network access.
