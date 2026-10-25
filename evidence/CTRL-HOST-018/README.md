# CTRL-HOST-018 / CHG-034 — Slot Release v2

Status: implementation evidence, pre-merge.

The live reproduction used `timeout 25s cap-plane-queue` and returned exit 124.
The installed helper held `/run/cap-plane-queue.lock` while performing the fresh
snapshot and then entered AUTO_NEXT health/GitHub reads. The root endpoint itself
responded immediately to an unauthenticated probe, so this was not a Plane outage
or stale-lock condition. The deterministic cost was the serial 1.25 second pacing
for the 18-request snapshot plus unbounded health work under the same lock.

The implementation keeps the lock and GET-only boundary, bounds advisory health,
and makes semantic slot release independent of lifecycle state. Binding/audit
history remains available to DONE and integrated acceptance paths.

Focused verification:

- `python3 -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -v` — 27 passed
- `python3 -m unittest discover -s tools/host/plane-transition -p 'test_*.py' -v` — 252 passed
- `python3 -m compileall -q tools/host/plane-queue tools/host/plane-transition tools/projectctl/src/projectctl` — passed

Live deployment and post-deploy queue readback remain pending until the merged
reference source is installed by the supported root-only installer.
