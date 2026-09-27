# Test 3 — Checkpoint/suspend-resume (ckpt1/ckpt2)

**Goal:** does a task keep its counter state across suspend/resume?

## Setup
A task writes a counter to a file every 5 s (30 iterations), POSTs to the receiver at the end.
- `ckpt1`: state file in `/tmp` (ephemeral)
- `ckpt2`: state file in `/workspace` (durable, snapshot to rustfs)

## Results
| Task | Suspended at | Resume | Outcome |
|---|---|---|---|
| ckpt1 (/tmp) | 8/30 | fresh 0 | state LOST — the command starts from zero |
| ckpt2 (/workspace) | 10/30 | resuming_from 10 | continued 11→30, POST 200, file_persisted=true |

## Lessons
- **/workspace is the only durable path.** Snapshot to rustfs on suspend; /tmp and process memory are ephemeral.
- **Resume RERUNS spec.command from the start** — it is not a process checkpoint. Durability comes from the file, not the substrate.
- Tasks must be idempotent: read the state file first, then continue the loop.
- As in test 2 (conc1): resume after a "poisoned" run (no egress policy) does not help — delete + recreate.
