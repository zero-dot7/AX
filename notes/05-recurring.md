# Test 5 — Task cykliczny (cron1)

**Cel:** czy substrat wspiera wykonywanie cykliczne?

## Ustalenie
**Brak natywnego cron/schedule** w AX (sprawdzone: CRD schema, `ax --help` — tylko apply/get/describe/watch/ssh/suspend/resume/delete). Task to jednorazowy, immutable runnable.

## Test (wzorzec zastępczy)
Długowieczny task z pętlą wewnętrzną: 3 cykle POST co 20 s.

## Wynik
3/3 dostarczone (ts 1790526623 → 643 → 663, dokładnie co 20 s), po zakończeniu pętli task zostaje w Running/idle (nie usuwa się sam).

## Lekcje
- Cykliczność = task z pętlą wewnętrzną + stan w /workspace (dla resumability), **albo** zewnętrzny scheduler (system cron na hoście) sterujący `ax apply/resume`
- Po wyjściu z pętli task pozostaje Running/idle — bez auto-delete; dla jednorazowych tasków trzeba kasować ręcznie
