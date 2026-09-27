# Test 2 — Współbieżność (3 taski równolegle)

**Data:** 2026-09-27 · **Taski:** `conc1` (open-meteo), `conc2` (easypack24), `conc3` (Gemini)

## Co testowaliśmy
3 taski jednocześnie na 2-podowym workerpoolu, każda z własną polityką egress,
każdy POSTuje wynik na receiver :18080.

## Wynik
✅ 3/3 dostarczone (HTTP 200):
- conc1: Sanok 18.5°C / Kraków 19.9°C / Gdańsk 15.6°C
- conc2: 33 punkty, 32 Operating
- conc3: ciekawostka o Sanoku (Beksiński) po 1 retryu 503

## Lekcje
1. **Kolejność wdrożenia**: egress-policy wymaga istnienia aktora → `ax apply` → odczekać ~3 s →
   `kubectl-ate create egress-policy` → `ax resume`. Jeśli task zdążył pobiec bez polityki, bieg jest
   „zatruty" — delete + recreate (resume po crashu odtwarza martwy checkpoint i task natychmiast
   wraca do Suspended).
2. Parallel resume: ~40–90 s od resume do dostarczenia.
3. Python `open("~/...")` nie rozwija `~` → `os.path.expanduser()`.
