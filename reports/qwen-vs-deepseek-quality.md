# Porównanie jakości analizy: qwen3.8-flash vs DeepSeek V3.2

Zadanie: speeddial-analysis (ten sam payload, ten sam prompt, commit cf297d5)

- **qwen/qwen3.8-flash** (06/10, reasoning OFF): raport 14 538 znaków, koszt $0.0064
- **deepseek/deepseek-v3.2** (07/10): raport 6 612 znaków, koszt ~$0.0051

## Wiarygodność (weryfikacja w źródle app.js)

### DeepSeek — finding #1 ("krytyczny wyciek pamięci w waitTabsComplete, app.js:104")
FAŁSZ. Funkcja (rzeczywista linia 147) usuwa listener w OBU ścieżkach wyjścia
(`tabs.onUpdated → finish()` oraz `setTimeout(finish)` — obie wywołują
`removeListener`). Wycieku nie ma; numer linii też zmyślony (104 to `makeThumb`).
Pozostałe numery linii deepseek (89, 120, 144, 175, 402) również niedokładne.

### qwen — top findings (captureVisibleTab/focused:false, token-refresh race, scroll reset)
Zweryfikowane wcześniej jako trafne i z poprawnym kontekstem (proces fix-pipeline
8/10 realnych fixów, 97/97 testów PASS potwierdzało diagnozy).

## Porównanie merytoryczne

**qwen (14,5k znaków):**
- 4 bugi logiczne głęboko uzasadnione (captureVisibleTab vs fokus okna,
  ciche zaprzestanie auto-backup po wygaśnięciu tokena, utrata kafelków
  przy imporcie bez protokołu, reset scrolla przy render)
- Analiza bezpieczeństwa na poziomie eksperta: PKCE poprawne, `state`/CSRF
  w launchWebAuthFlow, ocena ryzyka storage.sync vs local
- Konkretne optymalizacje (debounce auto-backup, IndexedDB dla miniatur,
  mutex na refresh tokenu)

**deepseek (6,6k znaków):**
- Szerokie pokrycie kategorii (security/UX/architektura), sensowna struktura
- ALE: top finding krytyczny = fałszywy alarm; część punktów powtarza
  komentarze z kodu (np. "martwy kod" DBX_APP_KEY_FALLBACK to zapis z
  komentarzy, nie analiza); line refs nie trafiają
- Rozpoznanie OAuth+PKCE jako poprawnego — zgodne z qwen

## Werdykt

**qwen3.8-flash wygrywa jakością analizy** przy podobnym koszcie:
- precyzja: 0 fałszywych krytyków u qwen vs 1 u deepseek (w top finding!)
- głębokość: qwen argumentuje przyczynowo, deepseek kataloguje
- kwant: deepseek 2× krótszy, szybszy, ~20% tańszy

DeepSeek V3.2 nadaje się do szybkich przeglądów katologowych (checklisty,
triage), ale do analizy przyczynowej kodu qwen jest bardziej wiarygodny.
