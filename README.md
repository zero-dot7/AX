# AX substrate — test results

Practical evaluation of the AX task substrate (k3s, gVisor sandbox, egress policies) on a private server. All 5 planned tests completed 2026-09-27.

## Structure
- `HOWTO.md` — condensed operator guide (setup, egress, task lifecycle, pitfalls)
- `manifests/` — sanitized task manifests (secrets redacted, see Rules)
- `notes/` — per-test notes: what was tested, results, lessons
- `data/` — raw results delivered by tasks to the receiver

## Tests
| # | Test | Status | Note |
|---|------|--------|------|
| 1 | Agent loop (Gemini function calling) | ✅ 2026-09-27 | `notes/01-agent-loop.md` |
| 2 | Concurrency (3 tasks, different APIs) | ✅ 2026-09-27 | `notes/02-concurrency.md` |
| 3 | Checkpoint/suspend-resume | ✅ 2026-09-27 | `notes/03-checkpoint-suspend-resume.md` — `/workspace` is the only durable path; `/tmp` is ephemeral |
| 4 | Atespace isolation | ✅ 2026-09-27 | `notes/04-atespace-isolation.md` — full isolation; no policy = fail-closed |
| 5 | Recurring task | ✅ 2026-09-27 | `notes/05-recurring.md` — no native cron; internal loop or external scheduler |

## Rules
- **No secrets in the repo** — API keys (Gemini), tokens, certificates cut/replaced with `REDACTED` placeholder.
- Manifests inject the key via `spec.env` from an env file on the host (`gemini-key.env`, 0600); placeholder in the repo.
- Before every push: scan for `AIza…` **and** `AQ.…` key formats (AQ. is the current Gemini format and slips past AIza-only regexes!). History was reset once (orphan branch + force-push) because AQ. keys leaked into commits.
