# WP-CORE-004 supported start transition denied

Observed 2026-10-24 by Asrın Dündar's developer session.

The real `cap-plane-queue` returned current_task WP-CORE-004, state READY,
blocked false. It classified WP-CORE-005 as a verified deferred wait:
IN_PROGRESS + BLOCKED, WAITING_EXTERNAL_INTEGRATION_BINDINGS. The other
deferred work was VALIDATING + BLOCKED. No product readiness or dependency
rule was relaxed.

Dedicated implementation branch:
`wp/WP-CORE-004-temporal-genealogy`, based on main
`ff56cfeb3142a41e0eb77b0649e6d8ab0fb7c506`.
Start-work record commit: `0439921` (resolve the full SHA in Git history).

## Actual supported transition attempt

The first request included a `repo:` evidence reference. The helper rejected
that envelope with INVALID_EVIDENCE_REFS before any lifecycle mutation.
The request was corrected to the helper's supported `commit:<full SHA>`
reference, pointing to the pushed start-work commit. It requested only
READY -> IN_PROGRESS through `cap-plane-transition WP-CORE-004 IN_PROGRESS`.

The corrected request returned exit code 2:

```json
{"reason_code": "HEAVY_CORE_WIP_LIMIT", "result": "DENIED"}
```

The installed `/usr/local/libexec/cap-plane-transition` IN_PROGRESS evaluator
selects other assigned IN_PROGRESS issues directly and applies the heavy-Core
WIP guard to them. That selection does not exclude the verified deferred
WP-CORE-005 wait exposed by the queue. This is an operational guard mismatch;
it is not proof of a WP-CORE-004 product/dependency failure or a reason to
weaken canonical readiness.

## Consequence and remaining work

The supported transition did not succeed. WP-CORE-004 has not been advanced
by this session; its last verified live lifecycle is READY, unblocked.
No manufacturing-core code, canonical specification, control-plane helper,
assignment, or unrelated WP has been changed. The two existing untracked
Asrın audit files were left untouched. No normal development PR or DONE
claim is made from start documentation alone.

All product implementation and its required tests remain outstanding.
There are no passing product-test or integrated-readiness claims here.
The owner implementation remains authorized but cannot proceed through the
required supported lifecycle start until the installed operational guard is
resolved through its separately authorized control process. No additional
WP or control-item implementation is selected in this branch.

Once that operational issue is resolved, resume this branch, re-read the
live queue, perform the supported READY -> IN_PROGRESS transition, and
execute the full implementation plan in IMPLEMENTATION-START.md. DEP-029
still applies at INTEGRATION, unchanged.
