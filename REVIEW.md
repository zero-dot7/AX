# REVIEW.md — standard review w tym repo

Wdrożenie playbooka „How the Claude Code team does code review" (Anthropic, 15/10/2026) w skali solo-dev. Warstwy:

## 1. Pre-PR — pokazany wynik
Agent uruchamia testy/build i wkleja realny output. Zmiany UI: opis/screenshot zachowania. Bez tego PR nie jest kompletny.

## 2. AI review na każdym PR (workflow `ai-review`)
Dwa niezależne przebiegi (bug review + security review) czytają diff **przeciwko całemu repo i intencji PR**, nie diff w izolacji. Trzeci przebieg (verification) odrzuca findings niesprawdzalne wobec pełnej treści plików — filtr false positives. Wynik: jeden komentarz z tabelą findings + severity. Model: zmienna `REVIEW_MODEL` (łańcuch fallback na darmowe modele OpenRouter; klucz w sekrecie `OPENROUTER_API_KEY`).

## 3. Security blokujący
CRITICAL w warstwie security (lub bug) = check `ai-review` czerwony = brak merga. Sekrety skanuje `gitleaks` na każdym push/PR.

## 4. CI + PR template
`ci`: `node --check` każdego .js + pełne testy functional speed-dial (116) w headless chromium. Template PR wymusza sekcje Testing / Ryzyko / Revert plan.

## 5. Approval skalowany ryzykiem
Tier wynika ze **zmiany**, nie z autora: low → merge samodzielny; medium → przeczytaj tabelę AI review; high (auth/billing/auto-update/migracja/infra) → człowiek czyta diff linia po linii przed merge. AI approval nigdy nie zastępuje ludzkiego przy high.

## 6. Merge queue / rollout
W skali solo: kolejka zbędna, ale — duże zmiany najpierw na branch + PR (nie push na main), feature flagi dla zmian zachowania, staged rollout dla rozszerzeń (wersja Canary Chrome przed stable).

## 7. Rollback + incydenty
Revert plan w każdym PR (jeden krok). Po incydencie: wpis do `INCIDENTS.md` z pytaniem „która warstwa miała to złapać" i poprawką procesu — każdy incydent uszczelnia reviewera.

## Metryki
Cel jak u Anthropic: mniej rewertów, PR-y z merytorycznym feedbackiem (nie 0 komentarzy = nikt nie patrzył). Sprawdzaj co jakiś czas: % PR-ów z findings AI utrzymanymi po weryfikacji, czas cyklu, liczba rewertów.
