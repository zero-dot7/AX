# axbot test suite — methodology

Last verified: 29/09/2026 on serv2uk (k3s, substrate v0.2.0-9-gc7b54699).

## Two layers

1. **Offline** (`axbot_offline_tests.py`) — runs anywhere (no cluster, no Telegram).
   Imports the real `src/axbot.py` + `src/watcher.py` with a `FakeBot` and synthetic
   task events. Covers: command dispatch (`/gen`, `/apply`), watch arming,
   transient-error tolerance (3 consecutive misses), phase disambiguation
   (None = task gone vs "ERR" = transient), result-file delivery, state
   persistence across restarts. Idempotence: re-delivery of an already-sent
   result is a no-op (`sent_file` persistence).
   Result on 29/09/2026: **21/21 pass** (stable across runs #4–#6b).

2. **Live** (`axbot_live_tests.py`) — runs ON serv2uk only. Drives the real
   running unit (`systemctl --user restart axbot` per scenario) through the
   full path: `/gen` manifest → `/apply` → substrate task → result file in
   `~/ax-test/data/` → watcher delivery to Telegram → journal check →
   auto-delete → watch removal. Three scenarios (`t-api.py`, `t-calc.py`,
   `t-multi.py`) exercise single-API, compute-bound (fib(30) + primes), and
   multi-tool tasks.

## Driver notes (learned the hard way, 29/09/2026)

- The driver's `Ctx` must carry a **real `Watchers`** instance (state-only
  watch) — a bare stub without `.watchers` makes `/apply` swallow the watch
  with `'Ctx' object has no attribute 'watchers'`, so the watch never reaches
  `state.json` and delivery silently never happens (this cost run #6:
  21 pass / 6 fail, all live FAILs were driver artifacts).
- Substrate quirk: task phase stays `Running` forever (upstream issue #346
  family) — **never** wait for `Succeeded`; deliver on result-file existence
  (implemented in `watcher.py`).
- `ax restart` cycles of axbot during a suite are normally **forced by the
  tests themselves** (each scenario restarts the unit), not crashes.
- Egress race on apply: driver retries re-apply once ("egress race retry").

## Results archive

- `live-results.txt` — run #5 (pre-driver-fix): 21 pass / 6 fail (driver bug).
- `live-run6b.log` — run #6b (final): **22 pass / 4 fail**.
  - live-api: all green (deliver + auto-delete + journal).
  - live-multi: all green.
  - live-calc: 4 FAILs — task stuck in `Running`, no result file, CPU idle,
    zero POSTs to receiver. Root cause: **workspace initialization never
    boots the guest-sandbox** (runner-side, upstream #346 family — NOT an
    axbot bug). Sandbox lives, actor stats flow, but the task command never
    starts. Next step if revisited: `spec.debug: true` on the manifest, or
    close as blocked-upstream.

## Run #7 — 2026-09-29: FULL GREEN (27/27)

- Same substrate as #6/#6b (v0.2.0-9-gc7b54699, no reboot since Sep 26),
  same axbot code (post-watcher-fix), same driver.
- Result: offline 21/21 (from repo, `PYTHONPATH=axbot/src`), live 27/0 —
  including live-calc, which passed in ~4 min after one handled
  egress-race retry (`re-applied live-calc (egress race retry)` is the
  driver's built-in retry, logged as info, not a failure).
- Conclusion: upstream #346 is an **intermittent race, not a hard
  blocker**. On identical code+substrate it failed 4/4 in run #6b and
  passed in run #7. Treat #6b-style hangs as retry-able: re-apply the
  task before escalating (the driver does this automatically once;
  manual escalation = delete task + re-apply, then `spec.debug: true`).
- Evidence: `live-run7.log`; journal shows result→deliver→auto-delete
  for all three scenarios.

## Re-running

```bash
# offline (any machine with the repo)
PYTHONPATH=axbot/src python3 axbot/tests/live/axbot_offline_tests.py  # needs: pip install pyyaml
# (repo layout: sources under axbot/src, tests under axbot/tests/live —
#  run from the repo root with PYTHONPATH=axbot/src)

# live (on serv2uk, as hermes)
scp tests/live/*.py serv2uk:/tmp/
ssh serv2uk 'cd ~/axbot && setsid nohup python3 /tmp/axbot_live_tests.py > /tmp/live-run.log 2>&1 < /dev/null &'
tail -f /tmp/live-run.log
```
