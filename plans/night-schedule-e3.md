# E3 — nocny harmonogram realizacji kolejki (stan: 08/10 07:20 UTC)

## Stan
- Zrobione (12/22): conventional-commit (#39, 07/10), parse-duration (#40, 08/10), slug, rolling,
  titlecase, word-counts, chunk, ngrams, rle, expr-lex, expr-parse, expr-eval
- Zostało (10): parse-ini → template → parse-kv → semver → crontab-next → changelog →
  git-diff-stat → git-log-json → env-lint → parse-diff
- Wszystkie scenariusze (FEATURES: spec_file/branch/prompt_core/test_file/test_import) KOMPLETNE.
- Wszystkie renderowane yaml 15,5–17,7 kB — poniżej limitu 32 768 (fix `2d78d9d`: runtime-injekcja
  `__EXISTING_SRC__` z tarballa + twardy gate w render()).
- Hidden tests: tylko parse-ini (dispatch.py HIDDEN_TESTS); pozostałe — brak = krok 3.5 pomijany.
- Run parse-ini z 08/10 rano PRZERWANY (exit -15) — stan czysty, feature dalej w kolejce.

## Mechanizm (nic nie trzeba konfigurować)
- Cron slot1 20:30 UTC + slot2 03:00 UTC → `night.py` bez argumentów →
  `pick_feature()` = pierwszy feature z QUEUE, którego funkcji nie ma w `src/lab/__init__.py`
  (dedupe: `night-state.json` — drugi slot tej samej nocy nie powtórzy pierwszego).
- Po merge PR funkcja ląduje w main → kolejna noc bierze następny. Digest 06:30 UTC.
- GATE'y: quota Z.ai (5h/weekly → skip/pauza), repo dirty → stop, rozmiar yaml >32 768 → fail fast,
  honest-fail by design (parse-url-like) — nie traktować jako błąd infra.

## Harmonogram (2 sloty/noc → 5 nocy)

| Noc        | Slot1 20:30 UTC | Slot2 03:00 UTC |
|------------|-----------------|-----------------|
| 08→09/10   | parse-ini (W20) | template        |
| 09→10/10   | parse-kv        | semver          |
| 10→11/10   | crontab-next    | changelog       |
| 11→12/10   | git-diff-stat   | git-log-json    |
| 12→13/10   | env-lint        | parse-diff      |

Kolejność gwarantowana kolejnością w QUEUE; jeśli noc się przesunie (quota skip), kolejka
nie ucieka — wszystko bierze następny niezrobiony.

## Scenariusze (per feature — wspólne dla wszystkich)
1. preflight (quota, repo clean, spec istnieje)
2. render → yaml <32 768 B, placeholder `__GEMINI_KEY__` zachowany
3. scp serv2 → ax apply → egress-policy → resume; wynik z aktora (status/patch)
4. anti-echo injection check + skan sekretów w patchu
5. dispatch: patch apply → testy repo → hidden tests (parse-ini) → push branch → PR → MERGE
6. poranny digest 06:30 (podsumowanie + koszty)

## Rano po każdej nocy (kontrola, bez akcji jeśli OK)
- `ls -t ~/.hermes/profiles/ax-factory/cron/output/3827f50e504d/ | head -2` → log slotu
- PR-y: `gh pr list -R zero-dot7/agent-lab --state merged -L 2`
- FAIL = zbadać log; honest-fail celowy ≠ błąd infra.

## Koniec kolejki (prognoza: rano 13/10)
- 22/22 feature'y w main; raport zbiorczy z digestu 06:30 13/10.
