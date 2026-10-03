"""E3 feature configs: per-spec prompt core + deterministic tests.

Każdy feature = 1 task AX = 1 branch = 1 PR (zasada agent-lab).
Testy PISZEMY MY (deterministyczne) — model generuje tylko implementację (lekcje 291/292).
Testy jako LISTA LINII (lekcja 296); kolejność asercji wg WYSTĘPOWANIA (lekcja 303/304).
"""

# Wspólna preambuła promptu; {core} = per-feature, {spec} = treść specs/<file>
PROMPT_HEAD = (
    "Zaimplementuj w Pythonie funkcje opisana specyfikacja. Zwroc DOKLADNIE jeden blok kodu "
    "w markdown (```python ... ```), zaden tekst poza nim. "
    "Blok = pelna zawartosc pliku src/lab/__init__.py: kompletna samodzielna implementacja "
)

PROMPT_TAIL = (
    ", ZERO importow z innych modulow pakietu lab. "
    "PLIK src/lab/__init__.py ZAWIERA JUZ FUNKCJE PONIZEJ — skopiuj je DOKLADNIE 1:1 "
    "bez najmniejszej zmiany, dodaj tylko nowa funkcje i jej nazwe do __all__:\n"
    "```python\n{existing}\n```\n"
    "SPECYFIKACJA:\n{spec}"
)

FEATURES = {
    "wrap-lines": {
        "spec_file": "specs/wrap-lines.md",
        "branch": "feat/wrap-lines",
        "prompt_core": (
            "wrap w tym jednym pliku (def wrap(text: str, width: int = 80) -> list[str]), "
            "definicja __all__ = [\"wrap\"], "
            "linie wynikowe <= width znakow; slowo dluzsze niz width samo w linii bez dzielenia; "
            "width < 1 -> ValueError; strip leading/trailing whitespace; "
            "pusty/whitespace-only input -> []"
        ),
        "test_file": "tests/test_wrap_lines.py",
        "test_import": "from lab import wrap",
        "test_lines": [
            "assert wrap('aaa bbb ccc', 7) == ['aaa bbb', 'ccc'], 'greedy fill'",
            "assert wrap('aaa   bbb', 3) == ['aaa', 'bbb'], 'whitespace run = one separator'",
            "assert wrap('  a b  ', 10) == ['a b'], 'strip ends'",
            "assert wrap('a\\nb', 1) == ['a', 'b'], 'newline is whitespace'",
            "long = 'x' * 10",
            "assert wrap(long, 3) == [long], 'long word alone, unmodified'",
            "assert wrap('ab ' + long, 3) == ['ab', long], 'long word own line'",
            "assert wrap('   ', 5) == [], 'whitespace-only -> []'",
            "assert wrap('', 80) == [], 'empty -> []'",
            "for bad in (0, -2):",
            "    try:",
            "        wrap('x', bad); raise SystemExit('no ValueError for width=%d' % bad)",
            "    except ValueError:",
            "        pass",
            "assert wrap('aaa bbb ccc ddd', 11) == ['aaa bbb ccc', 'ddd'], 'max line width'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "slug": {
        "spec_file": "specs/slug.md",
        "branch": "feat/slug",
        "prompt_core": (
            "slug w tym jednym pliku (def slug(text: str) -> str), "
            "definicja __all__ = [\"slug\"], "
            "lowercase ASCII; ciag znakow nie-alfanumerycznych -> jeden '-'; "
            "strip leading/trailing '-'; brak znakow alfanumerycznych -> ''"
        ),
        "test_file": "tests/test_slug.py",
        "test_import": "from lab import slug",
        "test_lines": [
            "assert slug('Hello, World!') == 'hello-world', 'basic'",
            "assert slug('  a  b  ') == 'a-b', 'runs collapse, ends stripped'",
            "assert slug('') == '', 'empty'",
            "assert slug('---###---') == '', 'no alphanumerics'",
            "assert slug('Foo_Bar 123') == 'foo-bar-123', 'underscore is non-alnum'",
            "assert slug('ABC') == 'abc', 'lowercase'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "rolling": {
        "spec_file": "specs/rolling.md",
        "branch": "feat/rolling",
        "prompt_core": (
            "rolling_mean w tym jednym pliku (def rolling_mean(values: list[float], window: int) -> list[float]), "
            "definicja __all__ = [\"rolling_mean\"], "
            "result[i] = mean(values[i:i+window]); len = len(values)-window+1; "
            "window < 1 lub window > len(values) -> ValueError; kazda srednia to float"
        ),
        "test_file": "tests/test_rolling.py",
        "test_import": "from lab import rolling_mean",
        "test_lines": [
            "r = rolling_mean([1, 2, 3, 4], 2)",
            "assert r == [1.5, 2.5, 3.5], 'consecutive windows'",
            "assert all(isinstance(x, float) for x in r), 'floats'",
            "assert rolling_mean([5], 1) == [5.0], 'window=1'",
            "assert rolling_mean([1, 2, 3], 3) == [2.0], 'window=len'",
            "for bad_args in (([1, 2], 3), ([1], 0), ([1], -1)):",
            "    try:",
            "        rolling_mean(*bad_args); raise SystemExit('no ValueError for %r' % (bad_args,))",
            "    except ValueError:",
            "        pass",
            "assert rolling_mean([1, 2, 3, 4, 5], 2) == [1.5, 2.5, 3.5, 4.5], 'length n-w+1'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "titlecase": {
        "spec_file": "specs/titlecase.md",
        "branch": "feat/titlecase",
        "prompt_core": (
            "title w tym jednym pliku (def title(text: str) -> str), "
            "definicja __all__ = [\"title\"], "
            "slowo = ciag non-whitespace; pierwszy znak alfabetyczny uppercase, reszta lowercase; "
            "whitespace preserved exactly; slowa bez znakow alfabetycznych bez zmian; '' -> ''"
        ),
        "test_file": "tests/test_titlecase.py",
        "test_import": "from lab import title",
        "test_lines": [
            "assert title('hello world') == 'Hello World', 'basic'",
            "assert title('  foo   bar ') == '  Foo   Bar ', 'whitespace preserved'",
            "assert title(\"it's-ok\") == \"It's-ok\", 'first alpha upper, rest lower'",
            "assert title('123 456') == '123 456', 'no alpha unchanged'",
            "assert title('') == '', 'empty'",
            "assert title('mIxEd CaSe') == 'Mixed Case', 'lowercase rest'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "word-counts": {
        "spec_file": "specs/word-counts.md",
        "branch": "feat/word-counts",
        "prompt_core": (
            "word_counts w tym jednym pliku (def word_counts(text: str) -> dict), "
            "definicja __all__ = [\"word_counts\"], "
            "slowo = ciag non-whitespace; obetnij wiodace/koncowe znaki nie-alfanumeryczne; "
            "klucze lowercase (case-insensitive); puste slowa ignorowane; '' -> {}"
        ),
        "test_file": "tests/test_word_counts.py",
        "test_import": "from lab import word_counts",
        "test_lines": [
            "assert word_counts('Hello hello WORLD') == {'hello': 2, 'world': 1}, 'case-insensitive'",
            "assert word_counts(\"don't stop, stop!\") == {\"don't\": 1, 'stop': 2}, 'strip punctuation'",
            "assert word_counts('') == {}, 'empty'",
            "assert word_counts('   ') == {}, 'whitespace only'",
            "assert word_counts('123 123 9') == {'123': 2, '9': 1}, 'digits are words'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "chunk": {
        "spec_file": "specs/chunk.md",
        "branch": "feat/chunk",
        "prompt_core": (
            "chunk w tym jednym pliku (def chunk(values: list, size: int) -> list), "
            "definicja __all__ = [\"chunk\"], "
            "dzieli liste na kolejne kawalki dlugosci size, ostatni moze byc krotszy; "
            "porzadek zachowany; [] -> []; size < 1 -> ValueError"
        ),
        "test_file": "tests/test_chunk.py",
        "test_import": "from lab import chunk",
        "test_lines": [
            "assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]], 'last shorter'",
            "assert chunk([1, 2], 2) == [[1, 2]], 'exact fit'",
            "assert chunk([], 3) == [], 'empty input'",
            "src = [1, 2, 3]; chunk(src, 1); assert src == [1, 2, 3], 'input not modified'",
            "for bad in (0, -1):",
            "    try:",
            "        chunk([1], bad); raise SystemExit('no ValueError for size=%r' % bad)",
            "    except ValueError:",
            "        pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "ngrams": {
        "spec_file": "specs/ngrams.md",
        "branch": "feat/ngrams",
        "prompt_core": (
            "ngrams w tym jednym pliku (def ngrams(text: str, n: int) -> list), "
            "definicja __all__ = [\"ngrams\"], "
            "n-gramy slow (slowa = ciagi non-whitespace w kolejnosci wejscia); "
            "wynik = lista krotek (tuple, nie list); dlugosc wyniku = len(words)-n+1; "
            "n < 1 -> ValueError; n > len(words) -> []; pusty tekst -> []"
        ),
        "test_file": "tests/test_ngrams.py",
        "test_import": "from lab import ngrams",
        "test_lines": [
            "assert ngrams('a b c', 2) == [('a', 'b'), ('b', 'c')], 'bigrams'",
            "assert ngrams('a b c', 3) == [('a', 'b', 'c')], 'trigram exact'",
            "assert all(isinstance(g, tuple) for g in ngrams('a b c', 2)), 'tuples not lists'",
            "assert ngrams('a b', 5) == [], 'n > words'",
            "assert ngrams('', 2) == [], 'empty'",
            "try:",
            "    ngrams('a b', 0); raise SystemExit('no ValueError for n=0')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "rle": {
        "spec_file": "specs/rle.md",
        "branch": "feat/rle",
        "prompt_core": (
            "rle i unrle w tym jednym pliku (def rle(values: list) -> list, "
            "def unrle(pairs: list) -> list), definicja __all__ = [\"rle\", \"unrle\"], "
            "rle: kolaps kolejnych rownych elementow na pary (wartosc, licznik), "
            "kazdy licznik >= 1; unrle = odwrotnosc (round-trip unrle(rle(x)) == x); "
            "rle([]) == [] i unrle([]) == []; unrle para z licznikiem < 1 -> ValueError"
        ),
        "test_file": "tests/test_rle.py",
        "test_import": "from lab import rle, unrle",
        "test_lines": [
            "assert rle([1, 1, 2]) == [(1, 2), (2, 1)], 'collapse runs'",
            "assert rle([]) == [] and unrle([]) == [], 'empty'",
            "for x in ([], [1], [1, 1, 1], [1, 2, 1, 2], ['a', 'a', 'b']):",
            "    assert unrle(rle(list(x))) == list(x), 'round-trip %r' % (x,)",
            "try:",
            "    unrle([(1, 0)]); raise SystemExit('no ValueError for count=0')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "template": {
        "spec_file": "specs/template.md",
        "branch": "feat/template",
        "prompt_core": (
            "template w tym jednym pliku (def template(text: str, mapping: dict) -> str), "
            "definicja __all__ = [\"template\"], "
            "podstaw {key} z mapping; {{ i }} to literaly (a{{b}}c -> a{b}c); "
            "nieznany klucz -> ValueError z nazwa klucza w komunikacie; "
            "niesparowany { zostaw bez zmian; wstawione wartosci nie sa skanowane ponownie"
        ),
        "test_file": "tests/test_template.py",
        "test_import": "from lab import template",
        "test_lines": [
            "assert template('a{b}c', {'b': 'X'}) == 'aXc', 'basic'",
            "assert template('a{{b}}c', {}) == 'a{b}c', 'literal braces'",
            "assert template('{a}{a}', {'a': 'x'}) == 'xx', 'repeat'",
            "assert template('no { unmatched', {'a': '1'}) == 'no { unmatched', 'unmatched brace as-is'",
            "assert template('v={x}', {'x': '{y}'}) == 'v={y}', 'no rescan'",
            "try:",
            "    template('{zzz}', {}); raise SystemExit('no ValueError for unknown key')",
            "except ValueError as e:",
            "    assert 'zzz' in str(e), 'key name in message'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "parse-kv": {
        "spec_file": "specs/parse-kv.md",
        "branch": "feat/parse-kv",
        "prompt_core": (
            "parse_kv w tym jednym pliku (def parse_kv(text: str) -> dict), "
            "definicja __all__ = [\"parse_kv\"], "
            "linie key=value (split na PIERWSZYM =); wartosc moze byc w cudzyslowach "
            "z escape \\\" i zachowuje wewnetrzne spacje, cudzyslowy usuwane; "
            "linie # = komentarze; puste linie pomijane; klucze i wartosci bez cudzyslowow strip(); "
            "duplikat klucza -> ValueError z nazwa klucza; linia bez = (nie komentarz) -> ValueError"
        ),
        "test_file": "tests/test_parse_kv.py",
        "test_import": "from lab import parse_kv",
        "test_lines": [
            "assert parse_kv('a=1\\nb=2') == {'a': '1', 'b': '2'}, 'basic'",
            "assert parse_kv('a = 1 \\n  # comment\\n\\nb= x ') == {'a': '1', 'b': 'x'}, 'comments+strip'",
            "assert parse_kv('k=\"  spaced  \"') == {'k': '  spaced  '}, 'quoted keeps spaces'",
            "assert parse_kv('k=\"say \\\\\"hi\\\\\"\"') == {'k': 'say \"hi\"'}, 'escaped quote'",
            "assert parse_kv('url=http://x/?a=1&b=2') == {'url': 'http://x/?a=1&b=2'}, 'first = splits'",
            "try:",
            "    parse_kv('a=1\\na=2'); raise SystemExit('no ValueError for duplicate')",
            "except ValueError as e:",
            "    assert 'a' in str(e), 'key name in message'",
            "try:",
            "    parse_kv('no_equals_here'); raise SystemExit('no ValueError for missing =')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    # ---- FALA 2 (03/10): practical / dev-tooling, L4-L6 ----

    "semver": {
        "spec_file": "specs/semver.md",
        "branch": "feat/semver",
        "prompt_core": (
            "semver_valid i semver_cmp w tym jednym pliku, "
            "definicja __all__ = [\"semver_valid\", \"semver_cmp\"], "
            "walidacja i porownywanie wersji zgodnie z semver.org: "
            "MAJOR.MINOR.PATCH z opcjonalnym -prerelease i +build; "
            "bez wiodacych zer (poza \"0\"); prerelease = identyfikatory "
            "oddzielone kropkami [0-9A-Za-z-], identyfikatory calkowicie "
            "numeryczne bez wiodacych zer; build = kropkowane identyfikatory "
            "[0-9A-Za-z-] (wiodace zera dozwolone); semver_valid zwraca bool "
            "(bez prefixu v, bez czesciowych typu 1.2); semver_cmp zwraca "
            "-1/0/1 wg precedencji: numerycznie major/minor/patch, wersja "
            "BEZ prerelease jest WYZEJ niz z prerelease, identyfikatory "
            "prerelease porownywane parami (numeryczny < alfanumeryczny, "
            "numeryczne liczbowo, alfanumeryczne ASCII), mniej identyfikatorow "
            "= nizej przy rownych poprzednich; build ignorowane; semver_cmp "
            "rzuca ValueError przy niepoprawnym argumencie"
        ),
        "test_file": "tests/test_semver.py",
        "test_import": "from lab import semver_valid, semver_cmp",
        "test_lines": [
            "assert semver_valid('1.2.3') is True, 'basic'",
            "assert semver_valid('1.2.3-alpha.1') is True, 'prerelease'",
            "assert semver_valid('1.2.3-alpha.1+build.7') is True, 'build'",
            "assert semver_valid('0.0.0') is True, 'zeros'",
            "assert semver_valid('01.2.3') is False, 'leading zero'",
            "assert semver_valid('1.2') is False, 'partial'",
            "assert semver_valid('v1.2.3') is False, 'v prefix'",
            "assert semver_valid('1.2.3-01') is False, 'numeric prerelease zero'",
            "assert semver_valid('1.2.3+') is False, 'empty build'",
            "assert semver_cmp('1.2.3', '1.2.3') == 0, 'equal'",
            "assert semver_cmp('1.2.3', '1.2.4') == -1, 'patch'",
            "assert semver_cmp('2.0.0', '1.9.9') == 1, 'major'",
            "assert semver_cmp('1.0.0-alpha', '1.0.0') == -1, 'pre < release'",
            "assert semver_cmp('1.0.0-alpha', '1.0.0-alpha.1') == -1, 'fewer ids'",
            "assert semver_cmp('1.0.0-alpha.1', '1.0.0-alpha.beta') == -1, 'num < alpha'",
            "assert semver_cmp('1.0.0-alpha.1', '1.0.0-alpha.1+md5') == 0, 'build ignored'",
            "try:",
            "    semver_cmp('1.2', '1.2.3'); raise SystemExit('no ValueError')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "conventional-commit": {
        "spec_file": "specs/conventional-commit.md",
        "branch": "feat/conventional-commit",
        "prompt_core": (
            "parse_commit w tym jednym pliku (def parse_commit(msg: str) -> dict), "
            "definicja __all__ = [\"parse_commit\"], "
            "parsuje NAGLOWEK (pierwsza linia) komunikatu Conventional Commits; "
            "ksztalt: type(scope)!: description, scope i ! opcjonalne, dwukropek "
            "obowiazkowy; type = niepuste, wylacznie male litery ASCII; "
            "scope = niepuste, bez bialych znakow i bez ), None gdy brak; "
            "! bezposrednio przed dwukropkiem => breaking=True; description = "
            "wszystko po dwukropku z opcjonalnym JEDNYM wiodacym spacja "
            "usunietym, niepuste; wynik: {'type','scope','breaking',"
            "'description'}; ValueError gdy: brak dwukropka, pusty type, "
            "pusty scope, pusty description, wielkie litery w type; "
            "cialo po pustej linii ignorowane"
        ),
        "test_file": "tests/test_conventional_commit.py",
        "test_import": "from lab import parse_commit",
        "test_lines": [
            "assert parse_commit('feat: add login') == {'type': 'feat', 'scope': None, 'breaking': False, 'description': 'add login'}, 'simple'",
            "assert parse_commit('fix(auth): correct token refresh') == {'type': 'fix', 'scope': 'auth', 'breaking': False, 'description': 'correct token refresh'}, 'scope'",
            "assert parse_commit('feat(api)!: remove v1 endpoints')['breaking'] is True, 'breaking'",
            "assert parse_commit('chore:  double space kept')['description'] == ' double space kept', 'one space stripped'",
            "assert parse_commit('docs: read routes|paths')['description'] == 'read routes|paths', 'pipe kept'",
            "assert parse_commit('feat: x\\n\\nBody with: colon')['description'] == 'x', 'body ignored'",
            "assert parse_commit('refactor(core): a|b|c') == {'type': 'refactor', 'scope': 'core', 'breaking': False, 'description': 'a|b|c'}, 'pipes in desc'",
            "try:",
            "    parse_commit('feat add login'); raise SystemExit('no ValueError')",
            "except ValueError:",
            "    pass",
            "try:",
            "    parse_commit('FEAT: x'); raise SystemExit('no ValueError uppercase')",
            "except ValueError:",
            "    pass",
            "try:",
            "    parse_commit('feat(): x'); raise SystemExit('no ValueError empty scope')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "parse-duration": {
        "spec_file": "specs/parse-duration.md",
        "branch": "feat/parse-duration",
        "prompt_core": (
            "parse_duration w tym jednym pliku (def parse_duration(s: str)), "
            "definicja __all__ = [\"parse_duration\"], "
            "parsuje duration na sekundy: input = konkatenacja tokenow "
            "liczba+jednostka bez separatorow (np. 1h30m); jednostki: ms, s, "
            "m, h, d; liczba = wylacznie cyfry (nieujemna calkowita); kazda "
            "jednostka co najwyzej raz, powtorzenie => ValueError; wynik = "
            "suma, ms jako ulamek sekundy (500ms => 0.5), calkowite wyniki "
            "moga byc int lub float; ValueError (z tokeniem w tresci, jesli "
            "dotyczy) dla: pusty string, jednostka bez liczby (h), nieznany "
            "sufiks (1x), niecalkowita liczba (1.5h), smieci na koncu"
        ),
        "test_file": "tests/test_parse_duration.py",
        "test_import": "from lab import parse_duration",
        "test_lines": [
            "assert parse_duration('90s') == 90, 'seconds'",
            "assert parse_duration('1h') == 3600, 'hour'",
            "assert parse_duration('1h30m') == 5400, 'combo'",
            "assert parse_duration('2d') == 172800, 'days'",
            "assert parse_duration('500ms') == 0.5, 'ms fraction'",
            "assert parse_duration('1h0m') == 3600, 'zero allowed'",
            "for bad in ['', 'h', '1x', '1.5h', '1h30', '1m30s1m']:",
            "    try:",
            "        parse_duration(bad); raise SystemExit(f'no ValueError for {bad!r}')",
            "    except ValueError:",
            "        pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "crontab-next": {
        "spec_file": "specs/crontab-next.md",
        "branch": "feat/crontab-next",
        "prompt_core": (
            "cron_next w tym jednym pliku (def cron_next(expr: str, after: "
            "datetime)), definicja __all__ = [\"cron_next\"], "
            "najwczesniejszy datetime STDZIECZIE po 'after' spelniajacy "
            "5-polowe wyrazenie crontab; after = naiwny datetime; wynik "
            "ma sekundy=0 (rozdzielczosc minuty) i jest OSTRO wiekszy od "
            "after; pola: minuta (0-59), godzina (0-23), dzien miesiaca "
            "(1-31), miesiac (1-12 lub JAN-DEC), dzien tygodnia (0-7 lub "
            "SUN-SAT; 0 i 7 = niedziela); nazwy 3-literowe case-"
            "insensitive; skladnia pola: *, liczba, zakres a-b (wlacznie), "
            "krok */n lub a-b/n, listy po przecinku; standardowa regula "
            "crona dla dni: gdy OBA pola dni ograniczone (zadne nie jest *) "
            "=> spelnione jesli DOWOLNE pasuje, gdy jedno jest * => drugie "
            "musi pasowac; ValueError przy zlej liczbie pol, wartosciach "
            "poza zakresem, znieksztalconym polu; brak trafienia w 2 lata "
            "=> ValueError; skanowanie minuta po minucie jest akceptowalne"
        ),
        "test_file": "tests/test_crontab_next.py",
        "test_import": "from lab import cron_next",
        "test_lines": [
            "from datetime import datetime",
            "assert cron_next('30 2 * * *', datetime(2026,10,3,2,0)) == datetime(2026,10,3,2,30), 'daily 2:30'",
            "assert cron_next('30 2 * * *', datetime(2026,10,3,2,30)) == datetime(2026,10,4,2,30), 'strictly after'",
            "assert cron_next('*/15 * * * *', datetime(2026,10,3,10,7)) == datetime(2026,10,3,10,15), 'step minutes'",
            "assert cron_next('0 9-17 * * *', datetime(2026,10,3,18,0)) == datetime(2026,10,4,9,0), 'hour range'",
            "assert cron_next('0 0 1 * *', datetime(2026,10,3,0,0)) == datetime(2026,11,1,0,0), 'dom 1st'",
            "assert cron_next('0 0 * * SUN', datetime(2026,10,3,0,0)) == datetime(2026,10,4,0,0), 'sunday name'",
            "assert cron_next('0 0 * * 1', datetime(2026,10,3,0,0)) == datetime(2026,10,5,0,0), 'monday num'",  # 2026-10-03 sat
            "assert cron_next('30 4 1,15 * *', datetime(2026,10,3,0,0)) == datetime(2026,10,15,4,30), 'dom list'",  # 15.10.2026 thu
            "assert cron_next('0 0 29 2 *', datetime(2026,10,3,0,0)) == datetime(2028,2,29,0,0), 'leap day'",
            "try:",
            "    cron_next('* * *', datetime(2026,1,1)); raise SystemExit('no ValueError fields')",
            "except ValueError:",
            "    pass",
            "try:",
            "    cron_next('60 * * * *', datetime(2026,1,1)); raise SystemExit('no ValueError range')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "changelog": {
        "spec_file": "specs/changelog.md",
        "branch": "feat/changelog",
        "prompt_core": (
            "parse_changelog i render_changelog w tym jednym pliku, "
            "definicja __all__ = [\"parse_changelog\", \"render_changelog\"], "
            "parser i renderer formatu Keep-a-Changelog; parse_changelog "
            "zwraca liste wydanej {'version': str, 'date': str, 'sections': "
            "dict} w kolejnosci wystapienia; sections mapuje nazwe sekcji na "
            "liste wpisow; linie przed pierwszym naglowkiem wersji "
            "ignorowane; naglowek wersji: DOKLADNIE '## [version] - date' "
            "z pojedynczymi spacjami i data YYYY-MM-DD; kazda inna linia "
            "zaczynajaca sie od '## ' (poza poprawnym naglowkiem wersji) "
            "=> ValueError; naglowek sekcji: '### Name'; wpisy = linie od "
            "'- ' (tekst = reszta linii); naglowek sekcji przed pierwszym "
            "naglowkiem wersji => ValueError; pusty tekst => []; "
            "render_changelog tworzy kanoniczny dokument (zaczyna sie od "
            "'# Changelog') z rotacja round-trip: "
            "parse_changelog(render_changelog(p)) == p"
        ),
        "test_file": "tests/test_changelog.py",
        "test_import": "from lab import parse_changelog, render_changelog",
        "test_lines": [
            "TXT = '# Changelog\\n\\n## [1.0.0] - 2026-09-01\\n\\n### Added\\n- init\\n- cli\\n\\n### Fixed\\n- bug\\n\\n## [0.9.0] - 2026-08-01\\n\\n### Added\\n- first'",
            "exp = [{'version': '1.0.0', 'date': '2026-09-01', 'sections': {'Added': ['init', 'cli'], 'Fixed': ['bug']}}, {'version': '0.9.0', 'date': '2026-08-01', 'sections': {'Added': ['first']}}]",
            "assert parse_changelog(TXT) == exp, 'parse full'",
            "assert parse_changelog('') == [], 'empty'",
            "assert parse_changelog('# Title\\nintro\\n') == [], 'no versions'",
            "assert render_changelog(exp).startswith('# Changelog'), 'render head'",
            "assert parse_changelog(render_changelog(exp)) == exp, 'round-trip'",
            "assert parse_changelog(render_changelog(parse_changelog(TXT))) == parse_changelog(TXT), 'round-trip on TXT'",
            "try:",
            "    parse_changelog('## 1.0.0 - 2026-09-01\\n'); raise SystemExit('no ValueError')",
            "except ValueError:",
            "    pass",
            "try:",
            "    parse_changelog('### Added\\n- x\\n'); raise SystemExit('no ValueError section first')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "git-diff-stat": {
        "spec_file": "specs/git-diff-stat.md",
        "branch": "feat/git-diff-stat",
        "prompt_core": (
            "diff_stat w tym jednym pliku (def diff_stat(text: str) -> dict), "
            "definicja __all__ = [\"diff_stat\"], "
            "liczby dodanych/usunietych linii per plik z unified diff; "
            "sciezka pliku z linii '+++ b/...' (wszystko po tabulatorze "
            "ignorowane); gdy strona +++ to /dev/null (plik usuniety), "
            "sciezka z poprzedzajacej linii '--- a/...' zamiast tego; "
            "linie tresci zaczynajace sie od '+' (oprocz +++) liczone jako "
            "added, od '-' (oprocz ---) jako removed, atrybuowane do "
            "naglowka najblizszego pliku; naglowki @@ i linie kontekstowe "
            "ignorowane; linie diffa przed pierwszym naglowkiem pliku "
            "ignorowane; metadata (diff --git, index, mode) ignorowana; "
            "pusty input => {}"
        ),
        "test_file": "tests/test_git_diff_stat.py",
        "test_import": "from lab import diff_stat",
        "test_lines": [
            "D1 = 'diff --git a/src/l.py b/src/l.py\\nindex 123..456 100644\\n--- a/src/l.py\\n+++ b/src/l.py\\n@@ -1,3 +1,4 @@\\n ctx\\n-old\\n+new\\n+new2\\n'",
            "assert diff_stat(D1) == {'src/l.py': {'added': 2, 'removed': 1}}, 'basic'",
            "D2 = '--- a/dead.py\\n+++ /dev/null\\n@@ -1,2 +0,0 @@\\n-a\\n-b\\n'",
            "assert diff_stat(D2) == {'dead.py': {'added': 0, 'removed': 2}}, 'deleted file'",
            "D3 = 'diff --git a/x b/x\\nnew file mode 100644\\n--- /dev/null\\n+++ b/x.py\\n@@ -0,0 +1,2 @@\\n+one\\n+two\\n'",
            "assert diff_stat(D3) == {'x.py': {'added': 2, 'removed': 0}}, 'new file'",
            "D4 = 'random leading junk\\n+++only header, no body'",
            "assert diff_stat(D4) == {}, 'junk tolerated'",
            "assert diff_stat('') == {}, 'empty'",
            "D5 = D1 + '--- a/y.py\\n+++ b/y.py\\n@@ -1 +1 @@\\n-a\\n+b\\n'",
            "assert list(diff_stat(D5)) == ['src/l.py', 'y.py'], 'order kept'",
            "assert diff_stat(D5)['y.py'] == {'added': 1, 'removed': 1}, 'second file'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "git-log-json": {
        "spec_file": "specs/git-log-json.md",
        "branch": "feat/git-log-json",
        "prompt_core": (
            "git_log_json w tym jednym pliku (def git_log_json(text: str)), "
            "definicja __all__ = [\"git_log_json\"], "
            "strukturyzuje wyjscie 'git log --pretty=%h|%ad|%s': lista dictow "
            "{'hash','date','subject'} w kolejnosci wejscia; kazda niepusta "
            "linia to hash|data|temat (dwa separatory |), temat moze zawierac "
            "| => split na PIERWSZYCH dwoch |; numeracja linii 1-based po "
            "WSZYSTKICH liniach wejscia (puste licza sie do numeracji); "
            "puste/biale linie pomijane; niepusta linia bez dokladnie dwoch "
            "| => ValueError z numerem linii (1-based) w tresci; pusty input "
            "=> []"
        ),
        "test_file": "tests/test_git_log_json.py",
        "test_import": "from lab import git_log_json",
        "test_lines": [
            "assert git_log_json('abc123|2026-10-01|feat: init') == [{'hash': 'abc123', 'date': '2026-10-01', 'subject': 'feat: init'}], 'single'",
            "assert git_log_json('a1|d1|s|with|pipes')[0]['subject'] == 's|with|pipes', 'pipes in subject'",
            "assert git_log_json('a1|d1|x\\n\\n   \\na2|d2|y') == [{'hash': 'a1', 'date': 'd1', 'subject': 'x'}, {'hash': 'a2', 'date': 'd2', 'subject': 'y'}], 'blanks skipped'",
            "assert git_log_json('') == [], 'empty'",
            "try:",
            "    git_log_json('a1|d1|x\\nb2|d2|y\\nbad')",
            "    raise SystemExit('no ValueError')",
            "except ValueError as e:",
            "    assert '3' in str(e), f'line number in msg: {e}'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "env-lint": {
        "spec_file": "specs/env-lint.md",
        "branch": "feat/env-lint",
        "prompt_core": (
            "env_lint w tym jednym pliku (def env_lint(text: str)), "
            "definicja __all__ = [\"env_lint\"], "
            "linter pliku .env: zwraca liste findings (line_no, code, "
            "message) posortowana po numerze linii; numeracja 1-based; "
            "puste linie i linie z pierwszym niebialym znakiem # nigdy nie "
            "daja findings; jedna linia max JEDNO finding wg priorytetu: "
            "missing_eq > invalid_key > duplicate_key; missing_eq = nie-"
            "komentarz bez '='; invalid_key = klucz (przed pierwszym =, "
            "po strip) niezgodny z ^[A-Z][A-Z0-9_]*$ (puste klucze tez); "
            "duplicate_key = klucz zgodny z wzorcem, ale juz widziany "
            "wczesniej (porownanie po strip); wartosci nie sa badane, brak "
            "parsingu komentarzy inline; kazdy finding ma niepusta "
            "czytelna dla czlowieka tresc; pusty input => []"
        ),
        "test_file": "tests/test_env_lint.py",
        "test_import": "from lab import env_lint",
        "test_lines": [
            "f = env_lint('OK=1\\nno_equals\\nbad-key=2\\nlower=3\\nOK=9\\n\\n# comment BAD\\n')",
            "codes = [c for _, c, _ in f]",
            "assert codes == ['missing_eq', 'invalid_key', 'invalid_key', 'duplicate_key'], f'codes: {codes}'",
            "assert [n for n, _, _ in f] == [2, 3, 4, 5], 'line numbers'",
            "assert all(m for _, _, m in f), 'non-empty messages'",
            "assert env_lint('A=1\\nB = 2') == [], 'stripped keys valid'",
            "assert env_lint('  # indented comment') == [], 'comment indent'",
            "assert env_lint('') == [], 'empty'",
            "assert env_lint('=1')[0][1] == 'invalid_key', 'empty key'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "parse-diff": {
        "spec_file": "specs/parse-diff.md",
        "branch": "feat/parse-diff",
        "prompt_core": (
            "parse_diff w tym jednym pliku (def parse_diff(text: str)), "
            "definicja __all__ = [\"parse_diff\"], "
            "parser unified diff: lista rekordow plikow {'old_path': "
            "str-or-None, 'new_path': str-or-None, 'hunks': list} w "
            "kolejnosci wystapienia; sciezka = linia po '--- ' / '+++ ' "
            "bez zmian (prefiksy a/, b/ ZOSTAJA), wszystko po tabulatorze "
            "/dev/null => None; naglowek hunka '@@ -a[,b] +c[,d] @@' "
            "dodaje {'old_start': a, 'old_count': b, 'new_start': c, "
            "'new_count': d} jako int, brakujacy count = 1; linie tresci "
            "(+, -, spacja, '\\\\ No newline') ignorowane, jak rowniez "
            "metadata (diff --git, index, mode); ValueError gdy linia +++ "
            "bez poprzedzajacego pasujacego ---, lub znieksztalcony "
            "naglowek hunka; pusty input => []"
        ),
        "test_file": "tests/test_parse_diff.py",
        "test_import": "from lab import parse_diff",
        "test_lines": [
            "D = '--- a/src/l.py\\n+++ b/src/l.py\\n@@ -1,3 +1,4 @@\\n ctx\\n-old\\n+new\\n'",
            "assert parse_diff(D) == [{'old_path': 'a/src/l.py', 'new_path': 'b/src/l.py', 'hunks': [{'old_start': 1, 'old_count': 3, 'new_start': 1, 'new_count': 4}]}], 'basic'",
            "assert parse_diff('') == [], 'empty'",
            "DN = '--- /dev/null\\n+++ b/x.py\\n@@ -0,0 +1 @@\\n+only\\n'",
            "r = parse_diff(DN)[0]",
            "assert r['old_path'] is None and r['new_path'] == 'b/x.py' and r['hunks'] == [{'old_start': 0, 'old_count': 0, 'new_start': 1, 'new_count': 1}], 'new file'",
            "assert parse_diff('--- a/x\\n+++ b/x\\n@@ -5 +6 @@\\n')[0]['hunks'] == [{'old_start': 5, 'old_count': 1, 'new_start': 6, 'new_count': 1}], 'count default 1'",
            "assert parse_diff('--- a/y.py\\t2026-10-01\\n+++ b/y.py\\n@@ -1 +1 @@\\n')[0]['new_path'] == 'b/y.py', 'tab strip'",
            "try:",
            "    parse_diff('+++ b/orphan\\n'); raise SystemExit('no ValueError orphan')",
            "except ValueError:",
            "    pass",
            "try:",
            "    parse_diff('--- a/x\\n+++ b/x\\n@@ bad @@\\n'); raise SystemExit('no ValueError hunk')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
}
