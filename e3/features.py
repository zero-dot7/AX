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
    # ---- pipeline "testy dziennie" propozycja 1 (expr: lex -> parse -> eval) ----
    "expr-lex": {
        "spec_file": "specs/expr-lex.md",
        "branch": "feat/expr-lex",
        "prompt_core": (
            "expr_lex w tym jednym pliku (def expr_lex(src: str) -> list), "
            "definicja __all__ = [\"expr_lex\"], "
            "tokeny 2-krotki (kind, value) kind in NUM/OP/LPAREN/RPAREN, "
            "NUM = cyfry z opcjonalna jedna kropka wewnatrz (wartosc jako "
            "string doslowny), OP = + - * /, nawiasy LPAREN/RPAREN, "
            "whitespace pomijany, inny znak => ValueError z tym znakiem "
            "w message, pusty/whitespace-only input => [], brak walidacji "
            "gramatyki ('+ + 3' to poprawne 3 tokeny)"
        ),
        "test_file": "tests/test_expr_lex.py",
        "test_import": "from lab import expr_lex",
        "test_lines": [
            "assert expr_lex('2 + 3 * (4 - 1)') == [('NUM','2'),('OP','+'),('NUM','3'),('OP','*'),('LPAREN','('),('NUM','4'),('OP','-'),('NUM','1'),('RPAREN',')')], 'basic'",
            "assert expr_lex('3.14') == [('NUM','3.14')], 'float literal kept as string'",
            "assert expr_lex('.5') == [('NUM','.5')], 'leading dot'",
            "assert expr_lex('1\\t+2') == [('NUM','1'),('OP','+'),('NUM','2')], 'tab is whitespace'",
            "assert expr_lex('') == [], 'empty'",
            "assert expr_lex('   ') == [], 'whitespace-only'",
            "assert expr_lex('1 2') == [('NUM','1'),('NUM','2')], 'no grammar validation'",
            "assert expr_lex('+ + 3') == [('OP','+'),('OP','+'),('NUM','3')], 'grammar-agnostic'",
            "try:",
            "    expr_lex('1 + a'); raise SystemExit('no ValueError for bad char')",
            "except ValueError as e:",
            "    assert 'a' in str(e), 'message contains offending char'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "expr-parse": {
        "spec_file": "specs/expr-parse.md",
        "branch": "feat/expr-parse",
        "prompt_core": (
            "expr_parse w tym jednym pliku (def expr_parse(tokens: list) -> dict), "
            "definicja __all__ = [\"expr_parse\"], AST: lisc {'type':'num','value':float}, "
            "binop {'type':'binop','op':str,'left':node,'right':node}; gramatyka "
            "expr:=term (('+'|'-') term)*, term:=factor (('*'|'/') factor)*, "
            "factor:=NUM | '(' expr ')' | ('-'|'+') factor; obsluga prefixu "
            "DOKLADNIE taka: nast = parse_factor(); jesli nast['type']=='num': "
            "return {'type':'num','value':-nast['value']} (negacja liscia!); "
            "w przeciwnym razie return {'type':'binop','op':'-','left':"
            "{'type':'num','value':0.0},'right':nast}; prefix '+' pomijamy; "
            "'-3*4' MUSI dac binop('*', num(-3.0), num(4.0)); "
            "NUM przez float(); malformed => ValueError (nadmiarowe "
            "tokeni po sparsowaniu, pusta lista, niezbalansowane nawiasy, operator "
            "tam gdzie czekamy factora, wiszacy operator); funkcja NIE wywoluje "
            "expr_lex, przyjmuje wylacznie tokeny"
        ),
        "test_file": "tests/test_expr_parse.py",
        "test_import": "from lab import expr_parse, expr_lex",
        "test_lines": [
            "assert expr_parse([('NUM','2')]) == {'type':'num','value':2.0}, 'leaf'",
            "N2 = {'type':'num','value':2.0}; N3 = {'type':'num','value':3.0}; N4 = {'type':'num','value':4.0}",
            "assert expr_parse(expr_lex('2+3*4')) == {'type':'binop','op':'+','left':N2,'right':{'type':'binop','op':'*','left':N3,'right':N4}}, 'precedence + consumes term'",
            "assert expr_parse(expr_lex('(2+3)*4')) == {'type':'binop','op':'*','left':{'type':'binop','op':'+','left':N2,'right':N3},'right':N4}, 'parens override'",
            "assert expr_parse(expr_lex('-3*4')) == {'type':'binop','op':'*','left':{'type':'num','value':-3.0},'right':N4}, 'unary binds tighter than *'",
            "assert expr_parse(expr_lex('2*-3')) == {'type':'binop','op':'*','left':N2,'right':{'type':'num','value':-3.0}}, 'unary in right factor'",
            "for bad_src, bad_why in [('1 2','leftover tokens'), ('','empty'), ('(1','unbalanced open'), ('1)','unbalanced close'), ('1 +','dangling op'), ('* 2','op where factor expected')]:",
            "    try:",
            "        expr_parse(expr_lex(bad_src)); raise SystemExit('no ValueError: %s' % bad_why)",
            "    except ValueError:",
            "        pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "expr-eval": {
        "spec_file": "specs/expr-eval.md",
        "branch": "feat/expr-eval",
        "prompt_core": (
            "expr_eval w tym jednym pliku (def expr_eval(ast: dict) -> float), "
            "definicja __all__ = [\"expr_eval\"], num => float(value), binop => "
            "rekurencyjnie left/right potem + - * /, dzielenie przez zero => "
            "naturalny ZeroDivisionError (nie lapac), nieznany type lub op => "
            "ValueError, czysta rekurencja bez eval()/exec()/importow; "
            "expr_lex i expr_parse (juz w pliku, skopiowane 1:1) maja zostac "
            "bez zmian — testy uruchamiaja caly pipeline end-to-end"
        ),
        "test_file": "tests/test_expr_eval.py",
        "test_import": "from lab import expr_eval, expr_parse, expr_lex",
        "test_lines": [
            "assert expr_eval({'type':'num','value':5}) == 5.0, 'leaf int-coerce'",
            "assert expr_eval(expr_parse(expr_lex('2 + 3 * (4 - 1)'))) == 11.0, 'end-to-end invariant'",
            "assert expr_eval(expr_parse(expr_lex('10 / 4'))) == 2.5, 'true division'",
            "assert expr_eval(expr_parse(expr_lex('-2 * 3'))) == -6.0, 'unary end-to-end'",
            "assert expr_eval(expr_parse(expr_lex('2 * (3 + 4) - 5'))) == 9.0, 'nested'",
            "try:",
            "    expr_eval(expr_parse(expr_lex('1/0'))); raise SystemExit('no ZeroDivisionError')",
            "except ZeroDivisionError:",
            "    pass",
            "try:",
            "    expr_eval({'type':'bad'}); raise SystemExit('no ValueError type')",
            "except ValueError:",
            "    pass",
            "try:",
            "    expr_eval({'type':'binop','op':'%','left':{'type':'num','value':1},'right':{'type':'num','value':2}}); raise SystemExit('no ValueError op')",
            "except ValueError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "report-aggregate": {
        "spec_file": "specs/report-aggregate.md",
        "branch": "feat/report-aggregate",
        "prompt_core": (
            "report_aggregate w tym jednym pliku (def report_aggregate("
            "commits: list)), definicja __all__ = [\"report_aggregate\"], "
            "agreguje wyjscie git_log_json: total=len(commits); typ commita "
            "= czesc subjecta przed pierwszym ':' ALE tylko gdy prefiks "
            "niepusty i wylacznie [A-Za-z0-9-] (inaczej 'other'), prefiks "
            "verbatim; by_type {typ: liczba} klucze sortowanie: count DESC "
            "potem typ ASC; by_date {data: liczba} klucze data ASC; zwrot "
            "DOKLADNIE {'total':int,'by_type':dict,'by_date':dict}; puste "
            "wejscie => {'total':0,'by_type':{},'by_date':{}}; nie mutowac "
            "wejscia; brak klucza 'subject' lub 'date' => KeyError "
            "(naturalny dostep do dicta)"
        ),
        "test_file": "tests/test_report_aggregate.py",
        "test_import": "from lab import report_aggregate, git_log_json",
        "test_lines": [
            "commits = git_log_json('h1|2026-10-01|feat: x\\nh2|2026-10-01|fix: y\\nh3|2026-10-02|feat: z\\nh4|2026-10-02|no colon here\\nh5|2026-10-01|Merge branch \\'main\\'')",
            "s = report_aggregate(commits)",
            "assert s['total'] == 5, 'total'",
            "assert list(s['by_type'].items()) == [('feat', 2), ('other', 2), ('fix', 1)], f\"by_type order: {s['by_type']}\"",
            "assert list(s['by_date'].items()) == [('2026-10-01', 3), ('2026-10-02', 2)], 'by_date order'",
            "assert report_aggregate([]) == {'total': 0, 'by_type': {}, 'by_date': {}}, 'empty'",
            "c2 = [{'hash':'a','date':'d','subject':'feat: x'}]",
            "assert report_aggregate(c2)['by_type'] == {'feat': 1}, 'single'",
            "try:",
            "    report_aggregate([{'hash': 'a'}]); raise SystemExit('no KeyError')",
            "except KeyError:",
            "    pass",
            "try:",
            "    report_aggregate([{'hash': 'a', 'date': 'd'}]); raise SystemExit('no KeyError subject')",
            "except KeyError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "report-render": {
        "spec_file": "specs/report-render.md",
        "branch": "feat/report-render",
        "prompt_core": (
            "report_render w tym jednym pliku (def report_render(summary: "
            "dict)), definicja __all__ = [\"report_render\"], renderuje "
            "wyjscie report_aggregate {'total','by_type','by_date'} do "
            "Markdowna. DOKLADNA konstrukcja zwrotki DOSLOWNYM pseudokodem "
            "(nic nie pomijaj, nic nie dodawaj):\n"
            "```\n"
            "lines = ['# Commit Report', '', 'Total: ' + str(total)]\n"
            "lines.append('')\n"
            "lines.append('## By type')\n"
            "if by_type:\n"
            "    lines.append('')\n"
            "    for k, v in by_type.items(): lines.append('- ' + k + ': ' + str(v))\n"
            "lines.append('')\n"
            "lines.append('## By date')\n"
            "if by_date:\n"
            "    lines.append('')\n"
            "    for k, v in by_date.items(): lines.append('- ' + k + ': ' + str(v))\n"
            "return chr(10).join(lines) + chr(10)\n"
            "```\n"
            "puste by_type/by_date => naglowek sekcji BEZ pustej linii za "
            "nim; pojedynczy trailing newline; czysta funkcja, nie mutuje "
            "wejścia; wzorcowy przyklad w specu jest DOSLOWNYM oczekiwanym "
            "wynikiem"
        ),
        "test_file": "tests/test_report_render.py",
        "test_import": "from lab import report_render, report_aggregate, git_log_json",
        "test_lines": [
            "expected = '# Commit Report\\n\\nTotal: 2\\n\\n## By type\\n\\n- feat: 1\\n- fix: 1\\n\\n## By date\\n\\n- 2026-10-01: 2\\n'",
            "summary = report_aggregate(git_log_json('h1|2026-10-01|feat: x\\nh2|2026-10-01|fix: y'))",
            "assert report_render(summary) == expected, f'pipeline: {report_render(summary)!r}'",
            "e2 = '# Commit Report\\n\\nTotal: 0\\n\\n## By type\\n\\n## By date\\n'",
            "assert report_render(report_aggregate([])) == e2, 'empty sections'",
            "assert not report_render(summary).endswith('\\n\\n'), 'single trailing newline'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "parse-url": {
        "spec_file": "specs/parse-url.md",
        "branch": "feat/parse-url",
        "prompt_core": (
            "parse_url w tym jednym pliku (def parse_url(url: str) -> dict), "
            "definicja __all__ = [\\\"parse_url\\\"], zwraca dict o DOKLADNIE "
            "6 kluczach {'scheme','host','port','path','query','fragment'}; "
            "algorytm DOSLOWNIE (nic nie pomijaj):\\n"
            "```\\n"
            "scheme, rest = url.split('://', 1)  # brak '://' lub pusty scheme => ValueError\\n"
            "scheme = scheme.lower()\\n"
            "if '#' in rest: rest, fragment = rest.split('#', 1)  # pierwszy '#', fragment bez '#'\\n"
            "else: fragment = ''\\n"
            "if '?' in rest: rest, qs = rest.split('?', 1)\\n"
            "else: qs = ''\\n"
            "if '/' in rest: host_port, path_tail = rest.split('/', 1); path = '/' + path_tail\\n"
            "else: host_port, path = rest, ''\\n"
            "if ':' in host_port: host, port_str = host_port.rsplit(':', 1)\\n"
            "  # UWAGA: z pustym port_str lub nie-liczba => ValueError;\\n"
            "  # port_str.isdigit() i int(port_str)\\n"
            "else: port = None\\n"
            "host = host.lower()\\n"
            "if not host: raise ValueError\\n"
            "query = {}\\n"
            "if qs:  # split po '&', kazdy element split po PIERWSZYM '=',\\n"
            "  # brak '=' => wartosc ''; powtorzone klucze: OSTATNIA wygrywa;\\n"
            "  # BEZ url-decode\\n"
            "return {'scheme':scheme,'host':host,'port':port,'path':path,'query':query,'fragment':fragment}\\n"
            "```\\n"
            "https://ex.com/k%20v?x=a%20b => query {'x':'a%20b'} (no decode); "
            "wzorcowe przyklady w specu sa DOSLOWNYMI oczekiwanymi wynikami"
        ),
        "test_file": "tests/test_parse_url.py",
        "test_import": "from lab import parse_url",
        "test_lines": [
            "assert parse_url('https://example.com') == {'scheme':'https','host':'example.com','port':None,'path':'','query':{},'fragment':''}, 'basic'",
            "r = parse_url('http://example.com:8080/a?b=1')",
            "assert r == {'scheme':'http','host':'example.com','port':8080,'path':'/a','query':{'b':'1'},'fragment':''}, 'port+path+query'",
            "r = parse_url('HTTP://ExAmple.COM')",
            "assert r['scheme'] == 'http' and r['host'] == 'example.com', 'case normalization'",
            "assert parse_url('https://ex.com/?a=1&a=2')['query'] == {'a':'2'}, 'dup key last wins'",
            "assert parse_url('https://ex.com/k%20v?x=a%20b')['query'] == {'x':'a%20b'}, 'no decode'",
            "r = parse_url('https://ex.com/p#frag')",
            "assert r['fragment'] == 'frag' and r['path'] == '/p', 'fragment'",
            "r = parse_url('ftp://files.example.com')",
            "assert r['path'] == '' and r['port'] is None and r['scheme'] == 'ftp', 'no path'",
            "for bad in ['example.com', '://x', 'https://', 'https://ex.com:', 'https://ex.com:abc/']:",
            "    try:",
            "        parse_url(bad); raise SystemExit('no ValueError: %s' % bad)",
            "    except ValueError:",
            "        pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "parse-url-tests": {
        "spec_file": "specs/parse-url.md",
        "branch": "feat/parse-url-tests",
        "answer_path": "tests/test_parse_url.py",
        "gate_file": "tests/test_zz_spec_gate.py",
        "prompt_core": (
            "Testuj FUNKCJE, nie implementacje: kazda asercja porownuje "
            "wynik parse_url(...) z oczekiwana wartoscia. Nie przepisuj kodu "
            "zrodlowego do testow. OSTATNIA linia pliku MUSI byc doslownie: "
            "print('ALL SPEC TESTS PASSED') — bez tego walidacja odrzuca prace."
        ),
        "prompt_head": (
            "Jestes inzynierem QA. Napisz plik testowy dla funkcji parse_url "
            "z pliku src/lab/__init__.py, ktorego pelny kod otrzymasz ponizej. "
            "Zwroc DOKLADNIE jeden blok kodu w markdown (```python ... ```), "
            "zaden tekst poza nim. Blok = pelna zawartosc pliku "
            "tests/test_parse_url.py."
        ),
        "prompt_tail": (
            "\nWYMAGANIA PLIKU TESTOWEGO:\n"
            "1. Na gorze: import sys; sys.path.insert(0, 'src'); "
            "from lab import parse_url\n"
            "2. Minimum 10 funkcji def test_*(), lacznie minimum 30 "
            "asercji assert. Kategorie obowiazkowe: happy path (scheme, host, "
            "port domyslny, path, query, fragment), port jawny, scheme/host "
            "wielkimi literami, path pusty vs sam ukośnik, query pusta, "
            "fragment pusty, zly scheme (ValueError), zly port (ValueError), "
            "brak hosta (ValueError).\n"
            "3. TYLKO czysty Python i assert — zadnego pytest, zadnych "
            "importow poza sys.\n"
            "4. Na koncu pliku DOSLOWNIE:\n"
            "if __name__ == '__main__':\n"
            "    _fns = [(n, f) for n, f in sorted(globals().items()) "
            "if n.startswith('test_') and callable(f)]\n"
            "    for _n, _f in _fns:\n"
            "        _f()\n"
            "    print('ALL TESTS PASSED (%d)' % len(_fns))\n"
            "KOD ZRODLOWY DO PRZETESTOWANIA (nie zmieniaj go, tylko testuj):\n"
            "```python\n{existing}\n```\n"
        ),
        "test_file": "tests/test_parse_url.py",
        "test_import": "from lab import parse_url",
        "test_lines": [
            "import re",
            "src = open('tests/test_parse_url.py', encoding='utf-8').read()",
            "assert len(re.findall(r'^def test_', src, re.M)) >= 10, 'za malo funkcji testowych'",
            "assert len(re.findall(r'\\bassert\\b', src)) >= 30, 'za malo asercji'",
            "assert 'pytest' not in src, 'zakaz pytest'",
            "assert src.count('def test_') == len(re.findall(r'^def test_', src, re.M)), 'def test_ tylko na poczatku linii'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "parse-url-harden": {
        "spec_file": "specs/parse-url.md",
        "branch": "feat/parse-url-harden",
        "prompt_core": (
            "W src/lab/__init__.py umozliwiaj current parse_url — NIE zmieniaj "
            "zachowania zpunktu widzenia istniejacych testow. Doloz wyłącznie "
            "hardening zgodnie z sekcja 8 specs/parse-url.md: "
            "a) userinfo: host_port zawiera '@' → usun wszystko do OSTATNIEGO "
            "'@' włącznie (reszta to host[:port]). "
            "b) IPv6: host_port zaczyna sie od '[' → host = zawartosc miedzy "
            "'[' a PIERWSZYM ']' (lowercase, bez nawiasow); port = po ']:'; "
            "']' przed '[' lub brak ']' → ValueError. "
            "c) port po int() musi byc 1..65535, inaczej ValueError. "
            "Nie ruszaj tests/. OSTATNIA linia zwracanego pliku MUSI byc "
            "doslownie print('ALL SPEC TESTS PASSED') — bez tego walidacja "
            "odrzuca prace."
        ),
        "test_file": "tests/test_zz_spec_gate.py",
        "test_import": "from lab import parse_url",
        "test_lines": [
            "def _ve(f):",
            "    try:",
            "        f()",
            "        return False",
            "    except ValueError:",
            "        return True",
            "r = parse_url('https://user@example.com')['host'] == 'example.com'",
            "r = r and parse_url('https://u:p@ex.com:8443/x')['port'] == 8443",
            "r = r and parse_url('https://[::1]:8080')['host'] == '::1'",
            "r = r and parse_url('https://[::1]:8080')['port'] == 8080",
            "r = r and parse_url('https://[::1]')['port'] is None",
            "r = r and parse_url('https://[Fe80::1]/a')['host'] == 'fe80::1'",
            "r = r and parse_url('https://ex.com:443/')['port'] == 443",
            "r = r and _ve(lambda: parse_url('https://ex.com:0/'))",
            "r = r and _ve(lambda: parse_url('https://ex.com:70000/'))",
            "r = r and _ve(lambda: parse_url('https://[::1/x'))",
            "r = r and _ve(lambda: parse_url('https://]weird[/x'))",
            "assert r, 'hardening edge-cases failed'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },

    "robust-parse": {
        'spec_file': 'specs/robust-parse.md',
        'branch': 'feat/robust-parse',
        'answer_path': 'src/lab/robust_parse.py',
        'gate_file': 'tests/test_zz_spec_gate.py',
        'prompt_head': 'Jestes inzynierem odpornosci (fuzzing). Napisz plik src/lab/robust_parse.py z funkcja parse_records odporna na dane adversarialne. Zwroc DOKLADNIE jeden blok kodu w markdown (```python ... ```), zaden tekst poza nim. Blok = pelna zawartosc pliku.',
        'prompt_core': 'Napisz plik src/lab/robust_parse.py zawierajacy DOKLADNIE jedna publiczna funkcje parse_records(text: str) -> list[dict]. Nie modyfikuj zadnego innego pliku.\nKONTRAKT parse_records:\n1. Non-str argument => raise TypeError (to JEDYNY dozwolony wyjatek).\n2. Podziel text na linie (str.splitlines). Puste linie / linie z samymi bialymi znakami POMIJANE.\n3. Dla kazdej linii s = line.strip():\n   - jesli zawiera "=": k, v = s.split("=", 1); key = k.strip(); value = v.strip(); jesli len(value) >= 2 i value zaczyna sie i konczy znakiem cudzyslowu podwojnego ", usun jeden poczatkowy i koncowy cudzyslow (zadne dodatkowe przetwarzanie escapow); wpis {"key": key, "value": value}.\n   - jesli NIE zawiera "=": wpis {"key": None, "value": None, "raw": s}.\n4. Zwroc liste w kolejnosci linii. Nie modyfikuj argumentu. Bez rekurencji.\n5. Przyklady:\n   parse_records(\'name = "Ada L"\\n empty= \\n broken\\n\\n\') == [{"key": "name", "value": "Ada L"}, {"key": "empty", "value": ""}, {"key": None, "value": None, "raw": "broken"}]\n   parse_records(\'a=1\\na=2\') == [{"key": "a", "value": "1"}, {"key": "a", "value": "2"}]\n   parse_records(\'a=b=c\') == [{"key": "a", "value": "b=c"}]\nNIE UZYWAJ wyrazen regularnych (podatnosc na catastrophic backtracking) - implementacja czysto iteracyjna (petle, str.split, str.strip). Funkcja dostanie adversarialne inputy (null bytes, surrogate U+D800, linie dlugosci 200000, 50000 linii) i dla KAZDEJ str musi zwrocic wynik bez zadnego wyjatku. Plik TYLKO ASCII, bez efektow ubocznych przy imporcie.',
        'prompt_tail': '\nSPEC (dla referencji, kontrakt powyzej jest wiazacy):\n```\n{spec}\n```\nPRZYKLADOWY KOD ZRODLOWY src/lab/__init__.py (konwencje pakietu):\n```python\n{existing}\n```\n',
        'test_file': 'src/lab/robust_parse.py',
        'test_import': 'from lab.robust_parse import parse_records',
        'test_lines': ['assert parse_records(\'name = "Ada L"\\n empty= \\n broken\\n\\n\') == [{"key": "name", "value": "Ada L"}, {"key": "empty", "value": ""}, {"key": None, "value": None, "raw": "broken"}]', 'assert parse_records(\'a=1\\na=2\') == [{"key": "a", "value": "1"}, {"key": "a", "value": "2"}]', 'assert parse_records(\'a=b=c\') == [{"key": "a", "value": "b=c"}]', "for bad in (None, 123, 4.5, [], {}, b'x'):", '    try:', '        parse_records(bad)', "        raise AssertionError('brak TypeError')", '    except TypeError:', '        pass', 'adv = [', "    'a=\\x00\\x00b',", "    '\\x00',", "    'k=\\ud800',", "    'x' * 200000 + '=1',", "    'v=' + 'y' * 200000,", "    'a' * 100000,", "    chr(10).join('k%d=v%d' % (i, i) for i in range(50000)),", "    '=',", "    '=v',", "    'k=',", '    \'"\',', '    \'""=""\',', "    '((((((((((((((((((=',", '    \'k="a\\x00b"\',', '    \'k="\\\\ud800"\',', "    '  \\t \\n \\r\\n ',", '    \'k = " v " \',', "    'na=5' * 4000,", "    '9' * 5000 + '.' + '9' * 5000 + '=1',", "    'k=v\\r\\nk2=v2\\r\\nk3',", ']', 'for i, s in enumerate(adv):', '    res = parse_records(s)', '    assert isinstance(res, list) and all(isinstance(d, dict) for d in res), i', 'assert parse_records(\'  k  =  "x"  \') == [{"key": "k", "value": "x"}]', 'assert parse_records(\'"abc\') == [{"key": None, "value": None, "raw": \'"abc\'}]', "print('ALL SPEC TESTS PASSED')"],
    },
    "api-docs": {
        "spec_file": "specs/api-docs.md",
        "branch": "feat/api-docs",
        "answer_path": "src/lab/api_docs.py",
        "gate_file": "tests/test_zz_spec_gate.py",
        "prompt_head": 'Jestes dokumentalista API. Napisz plik src/lab/api_docs.py bedacy dokumentacja API pakietu lab. Zwroc DOKLADNIE jeden blok kodu w markdown (```python ... ```), zaden tekst poza nim. Blok = pelna zawartosc pliku src/lab/api_docs.py.',
        "prompt_core": 'Utworz NOWY plik src/lab/api_docs.py: dokumentacja API pakietu lab jako module-level docstring z wykonywalnymi doctestami (format sekcji i wymagania ponizej). Plik = docstring + najwyzej importy, ZERO logiki i definicji. Kazda z 27 nazw publicznych lab.__all__ musi miec sekcje z opisem i przykladem \'>>>\', ktorego oczekiwany wynik jest DOSLOWNY (doctest porownuje znak po znaku - przesledz kod zrodlowy). Kazdy przyklad zaczyna sie wlasnym importem, np. >>> from lab import slug. Opisy po angielsku, plik TYLKO ASCII. Nie modyfikuj zadnego innego pliku.\nTRZY funkcje zyja w src/lab/reporting.py (kod ponizej, dokladnie ta semantyka):\n```python\nfrom __future__ import annotations\nimport re\n\n\ndef git_log_json(text: str) -> list[dict[str, str]]:\n    if not text:\n        return []\n\n    lines = text.splitlines()\n    result = []\n\n    for idx, line in enumerate(lines, start=1):\n        if not line.strip():\n            continue\n\n        parts = line.split(\'|\', 2)\n        if len(parts) != 3:\n            raise ValueError(f"Line {idx} does not contain exactly two \'|\' separators.")\n\n        commit_hash, date, subject = parts\n        result.append({\n            \'hash\': commit_hash,\n            \'date\': date,\n            \'subject\': subject\n        })\n\n    return result\n\n\ndef report_aggregate(commits: list[dict]) -> dict:\n    total = len(commits)\n    type_counts = {}\n    date_counts = {}\n\n    for commit in commits:\n        subj = commit[\'subject\']\n        dt = commit[\'date\']\n\n        if \':\' in subj:\n            prefix = subj.split(\':\', 1)[0]\n            if prefix and re.fullmatch(r\'[A-Za-z0-9-]+\', prefix):\n                commit_type = prefix\n            else:\n                commit_type = \'other\'\n        else:\n            commit_type = \'other\'\n\n        type_counts[commit_type] = type_counts.get(commit_type, 0) + 1\n        date_counts[dt] = date_counts.get(dt, 0) + 1\n\n    sorted_types = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))\n    by_type = {t: c for t, c in sorted_types}\n\n    sorted_dates = sorted(date_counts.items(), key=lambda item: item[0])\n    by_date = {d: c for d, c in sorted_dates}\n\n    return {\n        \'total\': total,\n        \'by_type\': by_type,\n        \'by_date\': by_date\n    }\n\n\ndef report_render(summary: dict, style: str = \'md\') -> str:\n    total = summary[\'total\']\n    by_type = summary[\'by_type\']\n    by_date = summary[\'by_date\']\n    lines = [\'# Commit Report\', \'\', \'Total: \' + str(total)]\n    lines.append(\'\')\n    lines.append(\'## By type\')\n    if by_type:\n        lines.append(\'\')\n        for k, v in by_type.items(): lines.append(\'- \' + k + \': \' + str(v))\n    lines.append(\'\')\n    lines.append(\'## By date\')\n    if by_date:\n        lines.append(\'\')\n        for k, v in by_date.items(): lines.append(\'- \' + k + \': \' + str(v))\n    if style == \'text\':\n        lines = [l[3:] if l.startswith(\'## \') else\n                 l[1:].lstrip() if l.startswith(\'#\') else l\n                 for l in lines]\n    elif style != \'md\':\n        raise ValueError(\'unknown style: \' + str(style))\n    return chr(10).join(lines) + chr(10)\n```\nPozostale 24 nazwy (wlacznie z klasa Template) sa eksportowane z src/lab/__init__.py - pelny kod na koncu promptu.',
        "prompt_tail": "\nFORMAT SEKCJI dla kazdej nazwy (wewnatrz module-level docstring):\n### <nazwa>(<sygnatura>)\n<jednozdaniowy opis po angielsku>\n>>> from lab import <nazwa>\n>>> <krotkie wywolanie>\n<dokladny wynik REPL, znak po znaku>\nWymagania: co najmniej 27 przykladow '>>>' lacznie; wyniki przelicz RECYTYWNIE z kodu zrodlowego (listy wypisuje sie w apostrofach, dict w kolejnosci wstawienia).\nKOD ZRODLOWY src/lab/__init__.py:\n```python\n{existing}\n```\n",
        "test_file": "src/lab/api_docs.py",
        "test_import": "import lab.api_docs",
        "test_lines": [
            'import doctest',
            'import lab',
            'res = doctest.testmod(lab.api_docs, verbose=False)',
            "assert res.failed == 0, 'doctest faili: %d' % res.failed",
            "assert res.attempted >= 27, 'za malo przykladow: %d' % res.attempted",
            "src = open('src/lab/api_docs.py', encoding='utf-8').read()",
            'missing = [n for n in lab.__all__ if n not in src]',
            "assert not missing, 'nieudokumentowane funkcje: %s' % missing",
            "assert '>>>' in src, 'brak doctest doctestow'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "compress-stats": {
        "spec_file": "specs/compress.md",
        "branch": "feat/compress-stats",
        "prompt_core": (
            "byte_histogram w tym jednym pliku (def byte_histogram(data) -> dict), "
            "dodaj nazwe do __all__. DODAJ TYLKO TE JEDNA funkcje byte_histogram "
            "(FUNKCJE rle_encode/rle_decode sa OSOBNYMI zadaniami — NIE dodawaj "
            "ich teraz). Wejscie bytes/bytearray (str => TypeError). "
            "Zwraca dict: klucz = wartosc bajtu (int 0..255) kazdego OBECNEGO "
            "bajtu, wartosc = liczba wystapien (>=1); nieobecne bajty NIE maja "
            "klucza. Puste wejscie => {}. Algorytm DOSLOWNIE:\\n"
            "```\\n"
            "if isinstance(data, str): raise TypeError\\n"
            "out = {}\\n"
            "for b in data:\\n"
            "    out[b] = out.get(b, 0) + 1\\n"
            "return out\\n"
            "```\\n"
            "sum(wartosci) == len(data). OSTATNIA linia zwracanego pliku MUSI "
            "byc doslownie print('ALL SPEC TESTS PASSED') — bez tego walidacja "
            "odrzuca prace."
        ),
        "test_file": "tests/test_compress_stats.py",
        "test_import": "from lab import byte_histogram",
        "test_lines": [
            "assert byte_histogram(b'') == {}, 'empty'",
            "assert byte_histogram(b'aaa') == {97: 3}, 'single run'",
            "assert byte_histogram(b'abca') == {97: 2, 98: 1, 99: 1}, 'counts'",
            "assert byte_histogram(bytes([0, 255, 0])) == {0: 2, 255: 1}, 'edge bytes'",
            "assert byte_histogram(bytearray(b'xyz')) == byte_histogram(b'xyz'), 'bytearray same as bytes'",
            "assert sum(byte_histogram(b'hello compress').values()) == 14, 'sum == len'",
            "try:",
            "    byte_histogram('abc'); raise SystemExit('no TypeError for str')",
            "except TypeError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "compress-encode": {
        "spec_file": "specs/compress.md",
        "branch": "feat/compress-encode",
        "prompt_core": (
            "rle_encode w tym jednym pliku (def rle_encode(data) -> bytes), "
            "dodaj nazwe do __all__. Wejscie bytes/bytearray (str => TypeError). "
            "RLE zachlanne: kazdy maksymalny run identycznych bajtow -> para "
            "(count, value); run dluzszy niz 255 dzielony na kolejne pary. "
            "Puste wejscie => b''. Algorytm DOSLOWNIE:\\n"
            "```\\n"
            "if isinstance(data, str): raise TypeError\\n"
            "out = bytearray()\\n"
            "i = 0\\n"
            "while i < len(data):\\n"
            "    v = data[i]\\n"
            "    j = i\\n"
            "    while j < len(data) and data[j] == v and j - i < 255:\\n"
            "        j += 1\\n"
            "    out += bytes([j - i, v])\\n"
            "    i = j\\n"
            "return bytes(out)\\n"
            "```\\n"
            "b'a'*300 => bytes([255, 97, 45, 97]). Wynik zawsze parzystej "
            "dlugosci. OSTATNIA linia zwracanego pliku MUSI byc doslownie "
            "print('ALL SPEC TESTS PASSED') — bez tego walidacja odrzuca prace."
        ),
        "test_file": "tests/test_compress_encode.py",
        "test_import": "from lab import rle_encode",
        "test_lines": [
            "assert rle_encode(b'') == b'', 'empty'",
            "assert rle_encode(b'a') == bytes([1, 97]), 'single byte'",
            "assert rle_encode(b'aaabbc') == bytes([3, 97, 2, 98, 1, 99]), 'basic runs'",
            "assert rle_encode(b'a' * 300) == bytes([255, 97, 45, 97]), 'run > 255 split'",
            "assert rle_encode(b'a' * 255) == bytes([255, 97]), 'exactly 255'",
            "assert rle_encode(b'a' * 256) == bytes([255, 97, 1, 97]), '256 split'",
            "assert rle_encode(bytes([0, 0, 0])) == bytes([3, 0]), 'zero byte value'",
            "assert len(rle_encode(bytes(range(256)))) == 512, 'no runs -> all pairs'",
            "try:",
            "    rle_encode('aaa'); raise SystemExit('no TypeError for str')",
            "except TypeError:",
            "    pass",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "compress-decode": {
        "spec_file": "specs/compress.md",
        "branch": "feat/compress-decode",
        "prompt_core": (
            "rle_decode w tym jednym pliku (def rle_decode(enc) -> bytes), "
            "dodaj nazwe do __all__. Wejscie bytes/bytearray (str => TypeError). "
            "Pary (count, value): kazda para rozwijana do value*count bajtow, "
            "sklejone. Nieparzysta dlugosc => ValueError; count == 0 => "
            "ValueError. Algorytm DOSLOWNIE:\\n"
            "```\\n"
            "if isinstance(enc, str): raise TypeError\\n"
            "if len(enc) % 2: raise ValueError('odd length')\\n"
            "out = bytearray()\\n"
            "for i in range(0, len(enc), 2):\\n"
            "    c = enc[i]\\n"
            "    if c == 0: raise ValueError('zero count')\\n"
            "    out += bytes([enc[i + 1]]) * c\\n"
            "return bytes(out)\\n"
            "```\\n"
            "KONTRAKT round-trip: rle_decode(rle_encode(x)) == x (rle_encode "
            "juz istnieje w pliku — nie zmieniaj go). OSTATNIA linia "
            "zwracanego pliku MUSI byc doslownie print('ALL SPEC TESTS "
            "PASSED') — bez tego walidacja odrzuca prace."
        ),
        "test_file": "tests/test_compress_decode.py",
        "test_import": "from lab import rle_decode, rle_encode",
        "test_lines": [
            "assert rle_decode(b'') == b'', 'empty'",
            "assert rle_decode(bytes([3, 97])) == b'aaa', 'single pair'",
            "assert rle_decode(bytes([255, 97, 45, 97])) == b'a' * 300, 'split runs join'",
            "assert rle_decode(bytes([2, 0])) == bytes([0, 0]), 'zero value byte'",
            "try:",
            "    rle_decode(b'aaa'); raise SystemExit('no ValueError odd len')",
            "except ValueError:",
            "    pass",
            "try:",
            "    rle_decode(bytes([0, 97])); raise SystemExit('no ValueError count 0')",
            "except ValueError:",
            "    pass",
            "for data in (b'hello world, hello compress!', bytes(range(256)), b'\\x00' * 1000):",
            "    assert rle_decode(rle_encode(data)) == data, 'round-trip failed'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "reporting-module": {
        "spec_file": "specs/reporting-module.md",
        "branch": "feat/reporting-module",
        "prompt_head": (
            "Zrealizuj zadanie MOVE-REFACTOR opisane specyfikacja. Zwroc DOKLADNIE DWA bloki kodu "
            "w markdown (```python ... ```), zaden tekst poza nimi. Kazdy blok zaczyna sie PIERWSZA linia "
            "dokladnie '# FILE: <sciezka>'. Blok 1 = pelna nowa zawartosc src/lab/__init__.py. "
        ),
        "prompt_core": (
            "MOVE-REFACTOR: przenies 3 funkcje raportowe (git_log_json, report_aggregate, report_render) "
            "z src/lab/__init__.py do NOWEGO modulu src/lab/reporting.py. W __init__.py USUN "
            "definicje tych funkcji i zaraz po __all__ dodaj linie: "
            "from lab.reporting import git_log_json, report_aggregate, report_render. "
            "__all__ bez zmian. Test tests/test_reporting.py NIE przechodzi (ModuleNotFoundError). "
            "WAZNE: to musi byc RE-EXPORT tej samej funkcji (lab.git_log_json IS lab.reporting.git_log_json), "
            "nie kopia definicji. src/lab/pipeline.py zostaje BEZ ZMIAN (dziala przez re-export). "
            "Wszystkie istniejace testy musza nadal przechodzic."
        ),
        "prompt_tail": (
            "Blok 2 = pelna zawartosc NOWEGO modulu src/lab/reporting.py z tymi 3 funkcjami "
            "skopiowanymi DOKLADNIE 1:1 z ponizszego pliku:\n"
            "```python\n{existing}\n```\n"
            "SPECYFIKACJA:\n{spec}"
        ),

        "test_lines": [
            'import sys',
            "sys.path.insert(0, 'src')",
            'import lab',
            'import lab.reporting as reporting',
            'from lab.pipeline import commit_report',
            '',
            '# re-export identity (nie kopia!)',
            "assert lab.git_log_json is reporting.git_log_json, 'identity git_log_json'",
            "assert lab.report_aggregate is reporting.report_aggregate, 'identity report_aggregate'",
            "assert lab.report_render is reporting.report_render, 'identity report_render'",
            '',
            "LOG = 'h1|2026-10-01|feat: x\\nh2|2026-10-01|fix: y'",
            "assert reporting.git_log_json(LOG)[0]['hash'] == 'h1'",
            "assert reporting.report_render({'total': 0, 'by_type': {}, 'by_date': {}}, 'text') == 'Commit Report\\n\\nTotal: 0\\n\\nBy type\\n\\nBy date\\n'",
            "assert commit_report(LOG, 'text').startswith('Commit Report'), 'pipeline przez re-export'",
            "print('ALL SPEC TESTS PASSED')",
        ],
        "test_file": "tests/test_reporting.py",
        "test_import": "import lab.reporting",
        "existing_test": True,
    },
    "csv-table": {
        "spec_file": "specs/csv-table.md",
        "branch": "feat/csv-table",
        "prompt_head": (
            "Zrealizuj zadanie opisane specyfikacja. Zwroc DOKLADNIE JEDEN blok kodu "
            "w markdown (```python ... ```) z pelna zawartoscia pliku src/lab/__init__.py. "
            "Zaden tekst poza blokiem. PIERWSZA linia bloku NIE moze zawierac '# FILE:'. "
        ),
        "prompt_core": (
            "Dodaj do src/lab/__init__.py na KONCU pliku dwie funkcje: csv_to_table oraz "
            "_csv_split, DOKLADNIE wg pseudokodu ze specyfikacji (sekcja Implementacja). "
            "Zachowaj wszystkie istniejace funkcje bez zadnych zmian. "
            "Test tests/test_csv_table.py NIE przechodzi na obecnym kodzie (brak csv_to_table). "
            "Wszystkie inne testy musza przechodzic."
        ),
        "prompt_tail": (
            "AKTUALNA zawartosc src/lab/__init__.py do modyfikacji:\n"
            "```python\n{existing}\n```\n"
            "SPECYFIKACJA:\n{spec}"
        ),
        "test_lines": [
            '',
            'CSV = \'name,amount\\nalice,"1,000"\\nbob,"say ""hi"""\\ncarol,3\\n\'',
            '',
            '# Markdown',
            'md = csv_to_table(CSV)',
            'assert md == (',
            "    '| name | amount |\\n'",
            "    '|---|---|'",
            "    '\\n| alice | 1,000 |'",
            '    \'\\n| bob | say "hi" |\'',
            "    '\\n| carol | 3 |'",
            '), repr(md)',
            '',
            '# HTML',
            "html = csv_to_table(CSV, 'html')",
            "assert '<table>' in html and html.startswith('<table>')",
            "assert '<th>name</th><th>amount</th>' in html, repr(html)",
            "assert '<td>alice</td><td>1,000</td>' in html",
            'assert \'<td>bob</td><td>say "hi"</td>\' in html',
            "assert html.rstrip().endswith('</table>')",
            '',
            '# domyslny fmt = md',
            "assert csv_to_table(CSV) == csv_to_table(CSV, 'md')",
            '',
            '# brak naglowka w html -> th w pierwszym wierszu, td dalej',
            "assert html.count('<th>') == 2 and html.count('<td>') == 6",
            '',
            '# wyjatki',
            'try:',
            "    csv_to_table('a,b\\n1,2,3\\n', 'md')",
            "    raise SystemExit('FAIL: no ValueError')",
            'except ValueError as e:',
            "    assert 'Inconsistent' in str(e), str(e)",
            'try:',
            "    csv_to_table('\\n \\n', 'md')",
            "    raise SystemExit('FAIL: no ValueError')",
            'except ValueError as e:',
            "    assert 'Empty' in str(e), str(e)",
            'try:',
            "    csv_to_table('a\\n1\\n', 'pdf')",
            "    raise SystemExit('FAIL: no ValueError')",
            'except ValueError as e:',
            "    assert 'Unknown format' in str(e), e",
            "print('ALL SPEC TESTS PASSED')",
        ],
        "test_file": "tests/test_csv_table.py",
        "test_import": "from lab import csv_to_table",
        "existing_test": True,
    },
    "rolling-fast": {
        "spec_file": "specs/rolling-fast.md",
        "branch": "feat/rolling-fast",
        "prompt_head": (
            "Zrealizuj zadanie REFACTOR opisane specyfikacja. Zwroc DOKLADNIE JEDEN blok kodu "
            "w markdown (\u0060\u0060\u0060python ... \u0060\u0060\u0060) z pelna zawartoscia pliku src/lab/__init__.py. "
            "Zaden tekst poza blokiem. PIERWSZA linia bloku NIE moze zawierac '# FILE:'. "
        ),
        "prompt_core": (
            "W src/lab/__init__.py zastap funkcje rolling_mean implementacja O(n) (sliding window, "
            "biezaca suma) DOKLADNIE wg pseudokodu ze specyfikacji. Zachowaj identyczne zachowanie: "
            "te same wyniki, ten sam wyjatek ValueError('Invalid window size') przy window<1 lub "
            "window>len(values), ten sam podpis (values: list[float], window: int) -> list[float]. "
            "Pozostale funkcje w pliku: skopiuj DOKLADNIE 1:1 bez zadnych zmian. "
            "Test tests/test_rolling_fast.py NIE przechodzi (za wolno na obecnym kodzie). "
            "Wszystkie inne testy musza przechodzic."
        ),
        "prompt_tail": (
            "AKTUALNA zawartosc src/lab/__init__.py do modyfikacji:\n"
            "```python\n{existing}\n```\n"
            "SPECYFIKACJA:\n{spec}"
        ),

        "test_lines": [
            'import sys, time',
            "sys.path.insert(0, 'src')",
            'from lab import rolling_mean',
            '',
            '# rownowaznosc na danych calkowitych (refactor bez regresji)',
            "assert rolling_mean([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5], 'equivalence basic'",
            "assert rolling_mean([5], 1) == [5.0], 'window=1'",
            "assert rolling_mean([1, 2, 3], 3) == [2.0], 'window=len'",
            "assert rolling_mean([-2, -1, 0, 1, 2], 2) == [-1.5, -0.5, 0.5, 1.5], 'negatives'",
            'data = list(range(1, 20001))',
            'w = 7',
            'r = rolling_mean(data, w)',
            "assert abs(r[0] - sum(data[:w]) / w) < 1e-9, 'first window'",
            "assert abs(r[-1] - sum(data[-w:]) / w) < 1e-9, 'last window'",
            "assert len(r) == len(data) - w + 1, 'length'",
            '',
            '# wydajnosc: O(n*w) na tym wejscu potrzebowaloby ~minut; O(n) < 2 s',
            'big = list(range(1000000))',
            't0 = time.monotonic()',
            'rb = rolling_mean(big, 500000)',
            'dt = time.monotonic() - t0',
            "assert len(rb) == 500001, 'big length'",
            "assert dt < 2.0, 'runtime %.2fs — za wolno (O(n*w)?)' % dt",
            "print('ALL SPEC TESTS PASSED (%.2fs)' % dt)",
        ],
        "test_file": "tests/test_rolling_fast.py",
        "test_import": "from lab import rolling_mean",
        "existing_test": True,
    },
    "pipeline-style": {
        "spec_file": "specs/pipeline-style.md",
        "test_import": "from lab.pipeline import commit_report",
        "branch": "feat/pipeline-style",
        "prompt_head": (
            "Zrealizuj zadanie CROSS-FILE-REFACTOR opisane specyfikacja. Zwroc DOKLADNIE DWA bloki kodu "
            "w markdown (```python ... ```), zaden tekst poza nimi. Kazdy blok zaczyna sie PIERWSZA linia "
            "dokladnie '# FILE: <sciezka>' (src/lab/__init__.py i src/lab/pipeline.py). "
            "Blok 1 = pelna nowa zawartosc src/lab/__init__.py. "
        ),
        "prompt_tail": (
            "Blok 2 = pelna zawartosc NOWEGO modulu src/lab/pipeline.py. "
            "PLIK src/lab/__init__.py ZAWIERA JUZ FUNKCJE PONIZEJ — w bloku 1 skopiuj je DOKLADNIE 1:1 "
            "bez najmniejszej zmiany, zmien tylko report_render i dodaj niczego nie usuwajac:\n"
            "```python\n{existing}\n```\n"
            "SPECYFIKACJA:\n{spec}"
        ),
        "existing_test": True,
        "prompt_core": (
            "CROSS-FILE-REFACTOR: spec specs/pipeline-style.md wymaga zmiany "
            "kontraktu: report_render(summary, style='md') w src/lab/__init__.py "
            "dostaje nowy parametr style ('md' default = dotychczasowe "
            "wyjscie; 'text' = naglowki bez '#'; inny -> ValueError). "
            "DODATKOWO stworz nowy modul src/lab/pipeline.py z funkcja "
            "commit_report(log_text, style='md') ktora wywoluje pipeline: "
            "git_log_json -> report_aggregate -> report_render(summary, style). "
            "Test tests/test_pipeline.py NIE przechodzi (ModuleNotFoundError). "
            "Zaktualizuj implementacje i dodaj caller SPOJNIE jednym patchem. "
            "PLIKU TESTU NIE ZMIENIAJ. Wszystkie istniejace testy musza nadal "
            "przechodzic (backward compat). Pseudokod w specu jest literalny."
        ),
        "test_file": "tests/test_pipeline.py",
        "test_lines": [
            'import sys',
            "sys.path.insert(0, 'src')",
            'from lab import report_render',
            'from lab.pipeline import commit_report',
            '',
            "LOG = 'h1|2026-10-01|feat: x\\nh2|2026-10-01|fix: y'",
            "summary = {'total': 2, 'by_type': {'feat': 1, 'fix': 1}, 'by_date': {'2026-10-01': 2}}",
            '',
            "assert commit_report(LOG) == report_render(summary), 'pipeline md == report_render md'",
            "expected_text = 'Commit Report\\n\\nTotal: 2\\n\\nBy type\\n\\n- feat: 1\\n- fix: 1\\n\\nBy date\\n\\n- 2026-10-01: 2\\n'",
            "assert commit_report(LOG, 'text') == expected_text, 'text style'",
            "assert commit_report(LOG, 'md') == report_render(summary), 'explicit md'",
            '# report_render text-style bezposrednio',
            "assert report_render(summary, 'text') == expected_text, 'report_render text'",
            '# nieznany styl',
            'try:',
            "    report_render(summary, 'bogus'); raise SystemExit('no ValueError for bogus style')",
            'except ValueError:',
            '    pass',
            'try:',
            "    commit_report(LOG, 'bogus'); raise SystemExit('no ValueError for bogus style (pipeline)')",
            'except ValueError:',
            '    pass',
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "repair-state": {
        "spec_file": "specs/repair-state.md",
        "test_import": "from lab import append_event",
        "branch": "feat/repair-state",
        "existing_test": True,
        "prompt_core": (
            "SELFSATISFIABLE-REPAIR: w repo jest funkcja append_event w "
            "src/lab/__init__.py z bugiem (stan przecieka miedzy wyolaniami). "
            "Test tests/test_append_event.py NIE przechodzi — przeczytaj go, "
            "zdiagnozuj ROOT CAUSE w implementacji i napraw implementacje. "
            "PLIKU TESTU NIE ZMIENIAJ. Diagnoza: mutable default argument "
            "jest wspoldzielony. Fix: log=None + log = list(log or []). "
            "Dodaj tylko naprawiona implementacje."
        ),
        "test_file": "tests/test_append_event.py",
        "test_lines": [
            "import sys",
            "sys.path.insert(0, 'src')",
            "from lab import append_event",
            "assert append_event('a') == ['a'], 'first call'",
            "assert append_event('b') == ['b'], 'state leaked between calls'",
            "assert append_event('x', ['a']) == ['a', 'x'], 'explicit log'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "repair-balanced": {
        "spec_file": "specs/repair-balanced.md",
        "branch": "feat/repair-balanced",
        "existing_test": True,
        "prompt_core": (
            "SELFSATISFIABLE-REPAIR: w repo jest funkcja is_balanced w "
            "src/lab/__init__.py z bugiem. Test tests/test_is_balanced.py "
            "NIE przechodzi. Znajdz root cause, napraw implementacje "
            "is_balanced w src/lab/__init__.py. Zakaz modyfikacji "
            "tests/test_is_balanced.py i kazdego innego pliku poza "
            "src/lab/__init__.py. Kontrakt: True gdy () [] {} poprawnie "
            "zbalansowane I poprawnie zagniezdzone (zamykanie w kolejnosci "
            "odwrotnej do otwierania, typy musza sie zgadzac). Zamkniecie "
            "bez otwarcia => False nawet gdy licznik sie wyrówna. "
            "Algorytm: stos otwartych nawiasow; przy zamknieciu wierzcholek "
            "stosu musi byc tego samego rodzaju; pusty stos przy zamknieciu "
            "=> False; na koncu stos pusty. Wymagane podejscie diagnostyczne: "
            "(1) odtworz failure lokalnie, (2) zidentyfikuj root cause, "
            "(3) dopiero wtedy popraw. OSTATNIA linia zwracanego pliku MUSI "
            "byc doslownie print('ALL SPEC TESTS PASSED') — bez tego "
            "walidacja odrzuca prace."
        ),
        "test_file": "tests/test_is_balanced.py",
        "test_import": "from lab import is_balanced",
        "test_lines": [
            "assert is_balanced('') is True, 'empty'",
            "assert is_balanced('()') is True, 'simple'",
            "assert is_balanced('([]{})') is True, 'nested ok'",
            "assert is_balanced('([)]') is False, 'crossed — the bug'",
            "assert is_balanced(')(') is False, 'close before open'",
            "assert is_balanced('(') is False, 'unclosed'",
            "assert is_balanced(')') is False, 'unopened'",
            "assert is_balanced('a(b[c]d)e') is True, 'ignore other chars'",
            "assert is_balanced('{[()]}') is True, 'deep nest'",
            "assert is_balanced('(()') is False, 'extra open'",
            "assert is_balanced('([)}') is False, 'crossed 2'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "multi-repair": {
        "spec_file": "specs/multi-repair.md",
        "branch": "feat/multi-repair",
        "existing_test": True,
        "prompt_core": (
            "SELFSATISFIABLE-REPAIR: w src/lab/__init__.py TRZY istniejace "
            "funkcje — top_lines, word_counts, append_event — zawieraja po "
            "JEDNYM subtelnym bugu. Test tests/test_multi_repair.py NIE "
            "przechodzi: dokladnie trzy asercje, po jednej na kazda funkcje. "
            "To zadanie CZYSTO DIAGNOSTYCZNE, bez podanego pseudokodu: "
            "(1) odtworz kazdy failure lokalnie, (2) zidentyfikuj ROOT CAUSE "
            "w implementacji (dokladna linia i mechanizm), (3) dopiero wtedy "
            "napraw. Zakaz modyfikacji plikow w tests/ i kazdego pliku poza "
            "src/lab/__init__.py. Nie dodawaj nowych funkcji — napraw "
            "istniejace tak, aby WSZYSTKIE testy repo przechodzily. "
            "OSTATNIA linia zwracanego pliku MUSI byc doslownie "
            "print('ALL SPEC TESTS PASSED') — bez tego walidacja odrzuca "
            "prace."
        ),
        "test_file": "tests/test_multi_repair.py",
        "test_import": "from lab import top_lines, word_counts, append_event",
        "test_lines": [
            "import sys",
            "sys.path.insert(0, 'src')",
            "from lab import top_lines, word_counts, append_event",
            "",
            "# top_lines: '#' liczy bonus wszedzie, nie tylko '# ' (C#, ###compact bez spacji)",
            "assert top_lines('plain text line\\nC# and dotnet', 1) == ['C# and dotnet'], 'hash anywhere counts'",
            "# word_counts: caly leading run znakow non-alnum jest usuwany",
            "assert word_counts('__hello__') == {'hello': 1}, 'strip whole leading non-alnum run'",
            "# append_event: przekazany log NIE moze byc mutowany w miejscu",
            "src = ['a']",
            "result = append_event('x', src)",
            "assert src == ['a'], 'input log must not be mutated'",
            "assert result == ['a', 'x'], 'returns new list with event'",
            '',
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "disp-width": {
        "spec_file": "specs/disp-width.md",
        "branch": "feat/disp-width",
        "prompt_head": "Zrealizuj zadanie opisane specyfikacja. Zwroc DOKLADNIE JEDEN blok kodu w markdown (```python ... ```) z pelna zawartoscia pliku src/lab/__init__.py. Zaden tekst poza blokiem. PIERWSZA linia bloku NIE moze zawierac '# FILE:'. ",
        "prompt_core": "Dodaj do src/lab/__init__.py funkcje disp_width, DOKLADNIE wg pseudokodu ze specyfikacji (sekcja Implementacja). Zachowaj wszystkie istniejace funkcje bez zadnych zmian. Linia print('ALL SPEC TESTS PASSED') musi pozostac OSTATNIA linia pliku — umiesc disp_width bezposrednio przed nia.",
        "prompt_tail": "AKTUALNA zawartosc src/lab/__init__.py do modyfikacji:\n```python\n{existing}\n```\nSPECYFIKACJA:\n{spec}",
        "existing_test": True,
        "test_file": "tests/test_disp_width.py",
        "test_import": "from lab import disp_width",
        "test_lines": [
            "import sys",
            "sys.path.insert(0, 'src')",
            "from lab import disp_width",
            "",
            "# disp_width: combining=0, CJK (W/F)=2, reszta=1",
            "assert disp_width('hello') == 5",
            "assert disp_width('') == 0",
            "assert disp_width('hé') == 2, 'latin-1 accent = 1 kolumna'",
            "assert disp_width('你好') == 4, 'CJK = 2 kolumny kazdy'",
            "assert disp_width('e\\u0301') == 1, 'combining mark = 0'",
            "assert disp_width('a🚀b') == 4, 'emoji (W) = 2 kolumny'",
            "assert disp_width('C# code') == 7",
            "assert disp_width('a\\u0301\\u0301') == 1, 'dwa combining marks = 0'",
            "assert disp_width('Ａ') == 2, 'fullwidth latin (F) = 2'",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "delta-codec": {
        "spec_file": "specs/delta-codec.md",
        "branch": "feat/delta-codec",
        "prompt_head": "Zrealizuj zadanie opisane specyfikacja. Zwroc DOKLADNIE JEDEN blok kodu w markdown (```python ... ```) z pelna zawartoscia pliku src/lab/__init__.py. Zaden tekst poza blokiem. PIERWSZA linia bloku NIE moze zawierac '# FILE:'. ",
        "prompt_core": "Dodaj do src/lab/__init__.py funkcje delta_encode i delta_decode, DOKLADNIE wg pseudokodu ze specyfikacji (sekcja Implementacja). Zachowaj wszystkie istniejace funkcje bez zadnych zmian. Linia print('ALL SPEC TESTS PASSED') musi pozostac OSTATNIA linia pliku — umiesc nowe funkcje bezposrednio przed nia.",
        "prompt_tail": "AKTUALNA zawartosc src/lab/__init__.py do modyfikacji:\\n```python\\n{existing}\\n```\\nSPECYFIKACJA:\\n{spec}",
        "existing_test": True,
        "test_file": "tests/test_delta_codec.py",
        "test_import": "from lab import delta_encode, delta_decode",
        "test_lines": [
            "import sys",
            "sys.path.insert(0, 'src')",
            "from lab import delta_encode, delta_decode",
            "import random",
            "",
            "rng = random.Random(20261004)",
            "",
            "# property: decode(encode(x)) == x, 500 losowych sekwencji",
            "for _ in range(500):",
            "    n = rng.randint(0, 40)",
            "    xs = [rng.randint(-1000, 1000) for _ in range(n)]",
            "    assert delta_decode(delta_encode(xs)) == xs, 'round-trip fail'",
            "",
            "assert delta_encode([]) == []",
            "assert delta_decode([]) == []",
            "assert delta_encode([5, 3, 10, 10]) == [5, -2, 7, 0]",
            "assert delta_decode([5, -2, 7, 0]) == [5, 3, 10, 10]",
            "",
            "# property: zgodnosc dlugosci",
            "for _ in range(100):",
            "    n = rng.randint(0, 20)",
            "    xs = [rng.randint(-50, 50) for _ in range(n)]",
            "    assert len(delta_encode(xs)) == len(xs), 'len mismatch'",
            "",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
    "template": {
        "spec_file": "specs/template.md",
        "feature_name": "template",
        "branch": "feat/template",
        "prompt_head": "Zrealizuj zadanie opisane specyfikacja. Zwroc DOKLADNIE JEDEN blok kodu w markdown (```python ... ```) z pelna zawartoscia pliku src/lab/__init__.py. Zaden tekst poza blokiem. PIERWSZA linia bloku NIE moze zawierac '# FILE:'. ",
        "prompt_core": "Dodaj do src/lab/__init__.py klase Template ( konstruktor Template(source), metoda render(ctx) ) DOKLADNIE wg kontraktu ze specyfikacji i tests/test_template.py. Zachowaj wszystkie istniejace funkcje bez zadnych zmian. Linia print('ALL SPEC TESTS PASSED') musi pozostac OSTATNIA linia pliku — umiesc klase bezposrednio przed nia. Tresc specyfikacji jest celowo minimalna: sam podejmij otwarte decyzje projektowe i UDOKUMENTUJ je w docstringu klasy Template.",
        "prompt_tail": "AKTUALNA zawartosc src/lab/__init__.py do modyfikacji:\\n```python\\n{existing}\\n```\\nSPECYFIKACJA:\\n{spec}",
        "existing_test": True,
        "test_file": "tests/test_template.py",
        "test_import": "from lab import Template",
        "test_lines": [
            "import sys",
            "sys.path.insert(0, 'src')",
            "from lab import Template",
            "",
            "# kontrakt z przykladami",
            "assert Template('Hello {name}').render({'name': 'World'}) == 'Hello World'",
            "assert Template('{a}+{a}={b}').render({'a': 2, 'b': 4}) == '2+2=4'",
            "assert Template('no placeholders').render({}) == 'no placeholders'",
            "assert Template('').render({'x': 1}) == ''",
            "assert Template('a{{b}}c').render({}) == 'a{b}c'",
            "assert isinstance(Template('v={v}').render({'v': [1]}), str)",
            "",
            "# brakujacy klucz -> KeyError",
            "try:",
            "    Template('{k}').render({})",
            "    raise AssertionError('brakujacy klucz: oczekiwano KeyError')",
            "except KeyError:",
            "    pass",
            "",
            "# decyzje projektowe udokumentowane w docstringu",
            "assert Template.__doc__ is not None and len(Template.__doc__.strip()) > 20, \\",
            "    'docstring klasy Template musi dokumentowac decyzje projektowe'",
            "",
            "print('ALL SPEC TESTS PASSED')",
        ],
    },
}
