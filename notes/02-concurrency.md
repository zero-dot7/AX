# Test 2 — Concurrency (3 tasks in parallel)

**Date:** 2026-09-27 · **Tasks:** `conc1` (open-meteo), `conc2` (easypack24), `conc3` (Gemini)

## What we tested
3 tasks at once on the 2-pod worker pool, each with its own egress policy,
each POSTing its result to the receiver on :18080.

## Result
✅ 3/3 delivered (HTTP 200):
- conc1: Sanok 18.5°C / Kraków 19.9°C / Gdańsk 15.6°C
- conc2: 33 points, 32 Operating
- conc3: a fact about Sanok (Beksiński) after 1× 503 retry

## Lessons
1. **Deployment order**: an egress policy requires the actor to exist → `ax apply` → wait ~3 s →
   `kubectl-ate create egress-policy` → `ax resume`. If the task managed to run without a policy,
   the run is "poisoned" — delete + recreate (resume after a crash restores a dead checkpoint and
   the task immediately falls back to Suspended).
2. Parallel resume: ~40–90 s from resume to delivery.
3. Python `open("~/...")` does not expand `~` → use `os.path.expanduser()`.
