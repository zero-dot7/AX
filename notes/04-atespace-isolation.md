# Test 4 — Izolacja atespace'ów (iso1/iso2)

**Cel:** czy dwa atespace'e (default, sandbox) są w pełni odizolowane?

## Setup
- 2 taski o tej samej nazwie `iso1` — jeden w `default`, drugi w `sandbox`, oba z własną egress-policy o tej samej nazwie
- Negatywny: `iso2` w `sandbox` **bez własnej polityki** (w `default` polityka iso1 istniała)

## Wyniki
- **Pozytywny:** oba `iso1` dostarczyły (PID 9 default, PID 10 sandbox) — nazwy tasków unikalne tylko per atespace, polityki per (atespace, aktor) nie kolidują
- **Negatywny:** iso2 zablokowany fail-closed (0 dostaw, Suspended) — polityka z default NIE przecieka do sandbox

## Lekcje
- Egress-policy scoped per (atespace, actor): `kubectl-ate create egress-policy <name> -a <atespace>`
- Brak polityki = block-all fail-closed, niezależnie od innych atespace'ów
- `ax get tasks` bez flagi pokazuje tylko default — używać `-A`/`-a`
- `ax resume/get/delete task X -a <atespace>` adresuje właściwy
