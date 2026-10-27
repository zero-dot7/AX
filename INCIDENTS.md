# INCIDENTS.md — rejestr incydentów

Po każdym incydencie (coś zmergowanego, co zepsuło się na main): data, PR, objaw, root cause, **która warstwa review miała to złapać**, poprawka procesu. Ten plik jest pamięcią reviewera — patterny z tutaj wpisów trafiają do promptów `ai-review`.

## Format

```
## YYYY-MM-DD — krótki tytuł
- PR: #N
- Objaw: ...
- Root cause: ...
- Która warstwa miała złapać: pre-PR / ai-review (bug) / ai-review (security) / gitleaks / ci / human (high-risk audit)
- Poprawka procesu: ... (co konkretnie zmieniono: prompt, workflow, template, REVIEW.md)
```

<!-- nowy wpis na górze -->
