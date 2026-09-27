# Test 1 — Pętla agentowa (Gemini function calling)

**Data:** 2026-09-27 · **Task:** `agent-loop1` · **Manifest:** `manifests/agent-loop1.yaml`

## Co testowaliśmy
Czy w tasku AX da się uruchomić prawdziwą pętlę agentową: model sam wybiera narzędzia
(function calling), iteruje i zatrzymuje się, gdy ma odpowiedź. Dotąd testowane taski
były deterministyczne (3 fazowy job).

## Narzędzia udostępnione modelowi
- `get_weather(city)` → open-meteo (geocoding + forecast)
- `find_paczkomaty(postcode)` → easypack24 (InPost)
- `calculate(expr)` → lokalny eval (bez sieci)

## Wynik
✅ E2E. 5 rund, model wywołał `get_weather(Sanok)` + `find_paczkomaty(38-500)` równolegle
w jednej rundzie, potem 3× `calculate` doprecyzowując liczbę punktów (33 → 32 → 29 paczkomatów).
Odpowiedź modelu: temperatura w Sanoku 18.9°C; dla kodu 38-500 działa 32 punktów InPost
(29 automatów), co jest +28% względem 25 (progu z pytania).

Retry+fallback znowu się przydał: `gemini-flash-latest` 2× 503 (high demand) → `gemini-flash-lite-latest`.
