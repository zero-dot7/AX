# Test 3 — Checkpoint/suspend-resume (ckpt1/ckpt2)

**Cel:** czy task po suspend/resume zachowuje stan licznika?

## Setup
Task pisze licznik do pliku co 5 s (30 iteracji), POST na receiver po zakończeniu.
- `ckpt1`: plik stanu w `/tmp` (ulotny)
- `ckpt2`: plik stanu w `/workspace` (durable, snapshot do rustfs)

## Wyniki
| Task | Suspend przy | Resume | Wynik |
|---|---|---|---|
| ckpt1 (/tmp) | 8/30 | fresh 0 | stan UTRACONY — komenda odpala od zera |
| ckpt2 (/workspace) | 10/30 | resuming_from 10 | kontynuacja 11→30, POST 200, file_persisted=true |

## Lekcje
- **/workspace to jedyna trwała ścieżka.** Snapshot do rustfs przy suspend; /tmp i pamięć procesu ulotne.
- **Resume RERUN'uje spec.command od początku** — to nie checkpoint procesu. Trwałość zapewnia plik, nie substrat.
- Taski muszą być idempotentne: najpierw czytają plik stanu, potem kontynuują pętlę.
- Podobnie jak w teście 2 (conc1): resume po „zatrutym" biegu (bez egress-policy) nie ratuje sytuacji — delete+recreate.
