# Test 1 — Agent loop (Gemini function calling)

**Date:** 2026-09-27 · **Task:** `agent-loop1` · **Manifest:** `manifests/agent-loop1.yaml`

## What we tested
Whether a real agent loop can run inside an AX task: the model picks tools itself
(function calling), iterates, and stops when it has the answer. Previous test tasks
were deterministic (3-phase jobs).

## Tools exposed to the model
- `get_weather(city)` → open-meteo (geocoding + forecast)
- `find_paczkomaty(postcode)` → easypack24 (InPost)
- `calculate(expr)` → local eval (no network)

## Result
✅ E2E. 5 rounds; the model called `get_weather(Sanok)` + `find_paczkomaty(38-500)` in parallel
in one round, then 3× `calculate` refining the point count (33 → 32 → 29 lockers).
Model answer: temperature in Sanok 18.9°C; for postcode 38-500, 32 InPost points operate
(29 machines), i.e. +28% over 25 (the threshold from the question).

Retry+fallback proved useful again: `gemini-flash-latest` 2× 503 (high demand) → `gemini-flash-lite-latest`.
