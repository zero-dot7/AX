# Test 4 — Atespace isolation (iso1/iso2)

**Goal:** are two atespaces (default, sandbox) fully isolated?

## Setup
- 2 tasks with the same name `iso1` — one in `default`, one in `sandbox`, each with its own egress policy of the same name
- Negative case: `iso2` in `sandbox` **without its own policy** (iso1's policy existed in `default`)

## Results
- **Positive:** both `iso1` tasks delivered (PID 9 default, PID 10 sandbox) — task names are unique only per atespace; policies per (atespace, actor) do not collide
- **Negative:** iso2 blocked fail-closed (0 deliveries, Suspended) — the policy from default does NOT leak into sandbox

## Lessons
- Egress policies are scoped per (atespace, actor): `kubectl-ate create egress-policy <name> -a <atespace>`
- No policy = block-all fail-closed, regardless of other atespaces
- `ax get tasks` without a flag shows only default — use `-A`/`-a`
- `ax resume/get/delete task X -a <atespace>` addresses the right one
