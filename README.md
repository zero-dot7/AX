# AX — Google Agent Executor substrate — eksperymenty

Prywatne notatki z eksperymentów na AX/ATE (Agent Executor + Agent Trust Engine)
uruchomionym na serv2uk (k3s, gVisor, worker-pool 2-podowy).

## Struktura
- `HOWTO-PL.md` — instrukcja obsługi substratu AX na serv2uk (CLI, cykl życia taska, egress, debug)
- `manifests/` — sanityzowane manifesty Task (klucz Gemini wycięty → `os.environ["GEMINI_API_KEY"]`)
- `data/` — wyniki dostarczone przez taski na receiver :18080 (JSON/MD)
- `notes/` — notatki z poszczególnych testów (co sprawdzaliśmy, wyniki, lekcje)

## Testy
| # | Test | Status | Note |
|---|------|--------|------|
| 1 | Pętla agentowa (Gemini function calling) | ✅ 2026-09-27 | `notes/01-agent-loop.md` |
| 2 | Współbieżność (3 taski, różne API) | ✅ 2026-09-27 | `notes/02-concurrency.md` |
| 3 | Checkpoint/suspend-resume | w toku | — |

## Zasady
- **Żadnych sekretów w repo** — klucze API (Gemini), tokeny, certyfikaty wycięte/zastąpione placeholderem `REDACTED`.
- Manifesty wstrzykują klucz przez `spec.env` z pliku env na hoście (`gemini-key.env`, 0600); w repo placeholder.
