import shutil, subprocess, sys, pathlib
REPO = pathlib.Path.cwd()  # run from the repository root
SRC = REPO / "services" / "manufacturing-simulator"
B = pathlib.Path(sys.argv[1])
MUT = {
 "M1 LIFO equal-time ties": ("events.py", "heapq.heappush(self._heap, (event.time, event.sequence, event))", "heapq.heappush(self._heap, (event.time, -event.sequence, event))"),
 "M2 clock may move backwards": ("clock.py", "        if time < self._now:", "        if False:"),
 "M3 stream seed depends on lookup order": ("rng.py", "spawn_key=(STREAM_IDS[key],)", "spawn_key=(len(self._streams) + 1,)"),
 "M4 quality shares failure stream id": ("rng.py", "StreamName.QUALITY: 5,", "StreamName.QUALITY: 3,"),
 "M5 failed handler leaves run READY": ("kernel.py", "        self._status = RunStatus.FAILED\n", "        self._status = RunStatus.READY\n"),
 "M6 event consumed before handler check": ("kernel.py", "        handler = self._handlers.get(event.kind)\n        if handler is None:", "        self._world.queue.pop()\n        handler = self._handlers.get(event.kind)\n        if handler is None:"),
 "M7 horizon inclusive off by one": ("kernel.py", "elif next_event.time > horizon:", "elif next_event.time >= horizon:"),
 "M8 budget checked before horizon": ("kernel.py", "            elif next_event.time > horizon:\n                reason = TerminationReason.HORIZON_REACHED\n            elif processed >= budget:\n                reason = TerminationReason.EVENT_LIMIT_REACHED\n", "            elif processed >= budget:\n                reason = TerminationReason.EVENT_LIMIT_REACHED\n            elif next_event.time > horizon:\n                reason = TerminationReason.HORIZON_REACHED\n"),
 "M9 global numpy RNG instead of named stream": ("rng.py", "generator = np.random.Generator(np.random.PCG64(sequence))", "generator = np.random.default_rng()"),
 "M10 worlds share one queue": ("scenario.py", "            queue=FutureEventQueue(),", "            queue=_SHARED,"),
 "M11 interruption not recorded (R2 reverted)": ("kernel.py", "        except BaseException as exc:\n", "        except ZeroDivisionError as exc:\n"),
 "M12 falsey payload silently dropped (R1 reverted)": ("scenario.py", '        raw_payload = data["payload"]\n', '        raw_payload = data["payload"] or {}\n'),
 "M13 malformed typed pair leaks raw error": ("events.py", 'raise InvalidConfigurationError("payload pairs must be (key, value)")', "pass"),
}
for name,(f,old,new) in MUT.items():
    d = B/"mut"; shutil.rmtree(d, ignore_errors=True); shutil.copytree(SRC, d, ignore=shutil.ignore_patterns("__pycache__","*.egg-info"))
    p = d/"src/manufacturing_simulator"/f; t = p.read_text()
    assert old in t, (name, "pattern missing")
    t = t.replace(old,new)
    if "_SHARED" in new: t = t.replace("class ScenarioEngine:", "_SHARED = FutureEventQueue()\n\n\nclass ScenarioEngine:")
    p.write_text(t)
    r = subprocess.run([sys.executable,"-m","pytest","-c",str(d/"pyproject.toml"),str(d/"tests"),"-q","-x","-p","pytest_quarantine"],capture_output=True,text=True,cwd=REPO)
    tail = [l for l in r.stdout.splitlines() if "passed" in l or "failed" in l][-1:]
    print(("CAUGHT  " if r.returncode else "SURVIVED"), name, tail)
