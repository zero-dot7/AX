#!/usr/bin/env python3
"""E3 dispatcher: wynik tasku AX (payload JSON) -> PR -> merge -> main.

Robi dokładnie to, co 01/10 zrobiono ręcznie dla wrap-lines:
  1. walidacja payloadu (status ok, ALL SPEC TESTS PASSED, patch niepusty)
  2. skan sekretów patcha (AIza…, AQ.A…, ghp_, sk-, GEMINI_API_KEY=)
  3. git pull main -> branch feat/<feature> -> git apply patch
  4. URUCHOMIENIE WSZYSTKICH TESTÓW tests/test_*.py (nie tylko nowego!)
     — bo model przepisuje caly src/lab/__init__.py i moze nadpisac
     istniejace funkcje (konflikt PR #1/#2, lekcja 01/10)
  5. commit (AX Lab Bot) -> push -> gh pr create -> gh pr merge --merge
  6. checkout main -> pull -> cleanup plikow tymczasowych

Użycie: dispatch.py <payload.json> <feature-name>
Env:   LAB_REPO (default /home/ubuntu/agent-lab)
Exit:  0 = merged; 3 = walidacja/skan FAIL (nic nie zpushowano).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.environ.get("LAB_REPO", "/home/ubuntu/agent-lab")
SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"AQ\.A[0-9A-Za-z_\-]{20,}"),
    re.compile(r"ghp_[0-9A-Za-z]{30,}"),
    re.compile(r"gho_[0-9A-Za-z]{30,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{20,}"),
    re.compile(r"GEMINI_API_KEY\s*="),
    re.compile(r"ZAI_API_KEY\s*="),
]
BRANCH_PREFIX = {"feat/", "fix/"}

# W20 hidden tests: edge-case'y NIEWIDOCZNE dla aktora; uruchamiane
# receive-side w dispatch.py PO standardowej walidacji, PRZEZ utworzeniem PR.
HIDDEN_TESTS = {
    "parse-ini": [
        # puste inputy
        "assert parse_ini('') == {}",
        "assert parse_ini('   \\n\\t\\n') == {}",
        # komentarze / puste linie
        "assert parse_ini('; c\\n[a]\\n# d\\nk=v') == {'a': {'k': 'v'}}",
        # strip wokol nazwy sekcji i klucza/wartosci
        "assert parse_ini('[ a ]\\n  k  =  v  ') == {'a': {'k': 'v'}}",
        # wartosc z '=' w srodku (pierwszy znak = dzieli)
        "assert parse_ini('[a]\\nk=a=b=c') == {'a': {'k': 'a=b=c'}}",
        # duplikat sekcji scala sie
        "assert parse_ini('[a]\\nx=1\\n[a]\\ny=2') == {'a': {'x': '1', 'y': '2'}}",
        # klucz przed sekcja -> ValueError
        "for bad in ['k=1', 'x = y\\n[a]']:",
        "    try:",
        "        parse_ini(bad); raise SystemExit('no ValueError: %r' % bad)",
        "    except ValueError:",
        "        pass",
        # NFD -> NFC normalizacja wartosci
        "import unicodedata",
        "nfd = 'e\\u0301'",
        "assert parse_ini('[a]\\nk=' + nfd)['a']['k'] == unicodedata.normalize('NFC', nfd)",
        # duze N: 5000 kluczy, sekcje sklejaja sie
        "big = '[s]\\n' + ''.join('k%d=v%d\\n' % (i, i) for i in range(5000))",
        "r = parse_ini(big)",
        "assert len(r['s']) == 5000 and r['s']['k4999'] == 'v4999'",
    ],
}


def run_hidden_tests(feature: str, repo: str = REPO) -> tuple[bool, str]:
    """W20: uruchom ukryte edge-case'y na branchu z patchem aktora.

    Import przez subproc z sys.path=src (wzorzec testow repo). Zwraca
    (ok, output). Nie modyfikuje drzewa (kod z stdout aktora juz applied).
    """
    lines = HIDDEN_TESTS.get(feature)
    if not lines:
        return True, "brak ukrytych testow dla tej featury"
    test_code = "\n".join(["import sys", "sys.path.insert(0, 'src')",
                           "from lab import " + feature.replace("-", "_"),
                           ""] + lines)
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     dir=os.path.join(repo, "tests")) as tf:
        tf.write(test_code)
        hidden_path = tf.name
    try:
        p = subprocess.run([sys.executable, hidden_path], cwd=repo,
                           capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(hidden_path)
    ok = p.returncode == 0
    return ok, ((p.stdout or "") + (p.stderr or ""))[-1500:]


def sh(cmd, cwd=None, check=True, timeout=120):
    p = subprocess.run(cmd, cwd=cwd or REPO, capture_output=True, text=True,
                       timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}): {' '.join(cmd)}\n"
                           f"stderr: {p.stderr[-600:]}")
    return p


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: dispatch.py <payload.json> <feature>", file=sys.stderr)
        return 2
    payload_path, feature = sys.argv[1], sys.argv[2]
    payload = json.load(open(payload_path, encoding="utf-8"))

    # 1) walidacja payloadu
    if payload.get("status") != "ok":
        print(f"VALIDATION FAIL: status={payload.get('status')!r}", file=sys.stderr)
        return 3
    tests_out = payload.get("results", {}).get("tests_out", "") \
        or payload.get("tests_out", "")
    if "ALL SPEC TESTS PASSED" not in tests_out:
        print(f"VALIDATION FAIL: tests_out missing PASS marker; tail="
              f"{tests_out[-200:]!r}", file=sys.stderr)
        return 3
    patch = payload.get("results", {}).get("patch") or payload.get("patch") or ""
    if not patch.strip():
        print("VALIDATION FAIL: empty patch", file=sys.stderr)
        return 3

    # 2) skan sekretów na patchu
    for pat in SECRET_PATTERNS:
        m = pat.search(patch)
        if m:
            # nie drukuj dopasowania (sekret!) — tylko wzorzec
            print(f"SECRET SCAN FAIL: pattern {pat.pattern} matched patch",
                  file=sys.stderr)
            return 3
    print("[1/6] payload OK, secret scan clean "
          f"(patch {len(patch)} B, feature {feature})")

    # 3) fresh main -> branch
    sh(["git", "checkout", "main", "-q"])
    sh(["git", "pull", "-q", "--ff-only"])
    branch = f"feat/{feature}"
    sh(["git", "branch", "-D", branch], check=False)  # poprzednia próba, jeśli była
    sh(["git", "checkout", "-q", "-b", branch])
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False) as tf:
        tf.write(patch)
        patch_file = tf.name
    try:
        sh(["git", "apply", "--check", patch_file])
        sh(["git", "apply", patch_file])
    finally:
        os.unlink(patch_file)
    changed = sh(["git", "status", "--porcelain"]).stdout.strip().splitlines()
    for line in changed:
        path = line[3:].strip()
        if path.startswith("specs/") or path == "README.md":
            print(f"VALIDATION FAIL: patch modyfikuje {path} (poza zakresem)",
                  file=sys.stderr)
            sh(["git", "checkout", "main", "-q"])
            return 3
    print(f"[2/6] patch applied: {len(changed)} file(s): "
          + ", ".join(line[3:].strip() for line in changed))

    # 4) WSZYSTKIE testy (safeguard nadpisania __init__.py)
    failed = []
    for tf_path in sorted(os.listdir(os.path.join(REPO, "tests"))):
        if not (tf_path.startswith("test_") and tf_path.endswith(".py")):
            continue
        p = sh(["python3", os.path.join("tests", tf_path)], check=False,
               timeout=120)
        if p.returncode != 0 or "ALL SPEC TESTS PASSED" not in p.stdout:
            failed.append(f"{tf_path}: rc={p.returncode} "
                          f"tail={p.stdout[-150:]!r} {p.stderr[-150:]!r}")
    if failed:
        print("TESTS FAIL (branch porzucony, PR NIE utworzony):",
              file=sys.stderr)
        for f in failed:
            print("  " + f, file=sys.stderr)
        # pełny rollback drzewa: porzucony patch NIE może zostawiać zmian
        # w drzewie (próba #1: dirty tree psuł {existing} w kolejnym renderze)
        sh(["git", "checkout", "main", "-q"])
        sh(["git", "reset", "--hard", "origin/main", "-q"])
        sh(["git", "clean", "-fd", "src", "tests"])
        return 3
    print("[3/6] wszystkie testy repo PASS")

    # W20: ukryte edge-case'y (niewidoczne dla aktora) na branchu
    ok, out = run_hidden_tests(feature)
    print(f"[3.5/6] hidden tests ({feature}): {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("HIDDEN TESTS FAIL (branch porzucony, PR NIE utworzony):\n" + out,
              file=sys.stderr)
        sh(["git", "checkout", "main", "-q"])
        sh(["git", "reset", "--hard", "origin/main", "-q"])
        sh(["git", "clean", "-fd", "src", "tests"])
        return 3

    # 5) commit -> push -> PR -> merge
    sh(["git", "add", "-A"])
    sh(["git", "-c", "user.name=AX Lab Bot",
        "-c", "user.email=324541862+zero-dot7@users.noreply.github.com",
        "commit", "-q", "-m",
        f"feat: implement {feature} per specs/{feature}.md\n\n"
        "Generated by AX sandbox task, validated by E3 dispatcher."])
    sh(["git", "push", "-q", "origin", branch])
    print(f"[4/6] pushed {branch}")
    sh(["gh", "pr", "create", "--fill-first", "--head", branch])
    pr_url = sh(["gh", "pr", "view", branch,
                 "--json", "url,number", "--jq", ".url + \" #\" + (.number|tostring)"]
                ).stdout.strip()
    print(f"[5/6] PR: {pr_url}")
    # GitHub potrzebuje chwili na przeliczenie mergeability po pushu
    import time
    for attempt in range(6):
        time.sleep(6)
        p = sh(["gh", "pr", "view", branch, "--json", "mergeable"],
               check=False)
        if '"MERGEABLE"' in p.stdout:
            break
    else:
        print("WARN: mergeable wciąż UNKNOWN — merge pominięty, PR otwarty",
              file=sys.stderr)
        sh(["git", "checkout", "main", "-q"])
        return 1
    sh(["gh", "pr", "merge", branch, "--merge"])
    print(f"[6/6] MERGED {pr_url}")

    # 6) powrót na main
    sh(["git", "checkout", "main", "-q"])
    sh(["git", "pull", "-q", "--ff-only"])
    sh(["git", "branch", "-d", branch], check=False)
    sh(["git", "push", "origin", "--delete", branch], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
