Offline WBS tooling for **CTRL-PM-001**, a control item outside the 179 canonical WPs.

With the declared dependencies already available locally:

```sh
python -m pip install --no-index --no-build-isolation -e 'tools/projectctl[test]'
projectctl parse
projectctl validate
projectctl status
python -B -m pytest tools/projectctl/tests
```

Alternatively, set `PYTHONPATH=tools/projectctl/src` and run `python -B -m projectctl`.
The CLI discovers the repository from the current directory or accepts `--root`.
`parse` emits JSON; `validate` and `status` also support `--json`.
Commands emit to stdout, never save generated state, and use no network clients.

Validation is limited to WBS syntax, owner resolution, capability index/card
agreement, local DoR/DoD references and the requested 179/29/owner baselines.
Requirement, architecture and dependency existence in other documents is not
verified. Raw expectations and source card spans are preserved; line numbers are
locations, not identity. Missing fields stay null. Raw `NOT_STARTED` is documentation
metadata and never becomes an execution state. No sync, READY or DONE operation exists.
