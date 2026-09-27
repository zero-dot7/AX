# Test 5 — Recurring task (cron1)

**Goal:** does the substrate support recurring execution?

## Finding
**No native cron/schedule** in AX (checked: CRD schema, `ax --help` — only apply/get/describe/watch/ssh/suspend/resume/delete). A task is a one-shot, immutable runnable.

## Test (substitute pattern)
A long-running task with an internal loop: 3 POST cycles every 20 s.

## Result
3/3 delivered (ts 1790526623 → 643 → 663, exactly every 20 s); after the loop ends the task stays Running/idle (it does not delete itself).

## Lessons
- Recurrence = a task with an internal loop + state in /workspace (for resumability), **or** an external scheduler (host cron) driving `ax apply/resume`
- After the loop exits the task remains Running/idle — no auto-delete; one-shot tasks must be deleted manually
