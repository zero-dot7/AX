#!/usr/bin/env python3
"""E3 task renderer: template + feature config -> rendered task YAML.

Użycie: python3 make_task.py <feature> [--out /tmp/x.rendered.yaml]

Wzorce z E2 (zweryfikowane): PROMPT standalone-string, testy jako lista linii,
model gemini-flash-lite-latest, REST single-shot z retry, tarball b64 embed,
diff unified przez difflib, POST na receiver :18080/<task-name>.
Klucz __GEMINI_KEY__ renderowany WYŁĄCZNIE server-side na serv2 (nigdy lokalnie).
RENDERED YAML Z KLUCZEM KASOWAĆ PO RUNIE (repo publiczne / bezpieczeństwo).
"""
import base64
import io
import os
import sys
import tarfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import FEATURES, PROMPT_HEAD, PROMPT_TAIL  # noqa: E402

TEMPLATE = "/home/ubuntu/ax/manifests/lab-toplines1.template.yaml"
REPO = "/home/ubuntu/agent-lab"


def git_show(repo: str, commit: str, path: str) -> str:
    """Zawartosc pliku z okreslonego commitu repo (nie drzewa roboczego!)."""
    import subprocess
    p = subprocess.run(["git", "show", f"{commit}:{path}"],
                       cwd=repo, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"git show {commit}:{path} failed: " + p.stderr.decode()[:200])
    return p.stdout.decode()


def make_tarball_b64(repo: str, commit: str = "HEAD") -> str:
    """Tarball repo z podanego commitu (default HEAD = main, bez .git)."""
    import subprocess
    p = subprocess.run(["git", "archive", "--format=tar.gz", commit],
                       cwd=repo, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("git archive failed: " + p.stderr.decode()[:200])
    return base64.b64encode(p.stdout).decode()


def tarball_gate(repo: str, commit: str, feature_name: str) -> None:
    """Gate: w tarballu zadania NIE WOLNO byc symbolu feature'u.

    Po merge'u feature'u na main tarball z HEAD zawieralby gotowe rozwiazanie
    -> modele robily by 'echo' gotowca (comparison 06/10 niewazny z tego powodu).
    Sprawdzamy plik docelowy (src/lab/__init__.py) na obecnosc symbolu.
    """
    import subprocess
    p = subprocess.run(["git", "show", commit + ":src/lab/__init__.py"],
                       cwd=repo, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("git show failed: " + p.stderr.decode()[:200])
    src = p.stdout.decode()
    candidates = ("class " + feature_name.capitalize(), "def " + feature_name)
    hits = [s for s in candidates if s in src]
    if hits:
        raise RuntimeError(
            "GATE: tarball base zawiera juz symbol feature'u (" +
            ", ".join(hits) + ") w src/lab/__init__.py — wybierz czystszy base_commit")


def render(feature_name: str, repo: str = REPO) -> str:
    f = FEATURES[feature_name]
    base_commit = f.get("base_commit", "HEAD")
    if base_commit != "HEAD":
        tarball_gate(repo, base_commit, feature_name)
    spec = git_show(repo, base_commit, f["spec_file"])
    inj = f.get("spec_inject")
    if inj:  # W21: injekcja doklejana do specu w PROMPCIE (repo bez zmian)
        spec = spec + inj
    existing = git_show(repo, base_commit, "src/lab/__init__.py")

    # Limit API: env AX_TASK_YAML <= 32768 znakow (CreateActorTemplate
    # InvalidArgument, run 07/10 20:30: task 35361 B -> aktor nie powstal ->
    # egress 12x FailedPrecondition -> exit 1). Model jest single-shot i MUSI
    # dostac pelny existing w PROMPCIE (clip 2500 B = falszywy VALIDATION FAIL,
    # run 21:55: przepisal __init__.py niekompletnie). Rozwiazanie: w yaml
    # zostaje token __EXISTING_SRC__, a pelny plik jest doklejany W RUNTIME
    # z rozpakowanego tarballa (repo na dysku sandboxa; tarball z base_commit).
    del existing
    existing = "__EXISTING_SRC__"

    head = f.get("prompt_head", PROMPT_HEAD)
    tail = f.get("prompt_tail", PROMPT_TAIL)
    prompt = head + f["prompt_core"] + tail.format(
        spec=spec,
        existing=existing,
    )

    # testy: preambuła (importy) + linie z configu — CAŁOŚĆ trafia do join([...])
    test_code_lines = ["import sys", "sys.path.insert(0, 'src')",
                       f["test_import"], ""] + f["test_lines"]
    lines_lit = ",\n                  ".join(repr(l) for l in test_code_lines)

    task_name = f"lab-{feature_name}"
    tmpl = open(TEMPLATE, encoding="utf-8").read()

    out = (tmpl
           .replace("lab-toplines1", task_name)
           .replace('"top-lines.md"', '"' + f["spec_file"].split("/")[-1] + '"')
           )
    # PROMPT: w template jest wielolinijkowy blok -> podmieniamy całą konstrukcję
    # (lambda w replacement: repr(prompt) zawiera \n, które re.sub by zinterpretowal)
    import re
    out = re.sub(
        r'PROMPT = \([\s\S]*?\+ spec\)',
        lambda m: 'PROMPT = ' + repr(prompt),
        out, count=1)
    # test_code: podmieniamy blok join([...]) na naszą listę linii
    out = re.sub(
        r'test_code = "\\n"\.join\([\s\S]*?\]\)',
        lambda m: "test_code = \"\\n\".join([\n                  " + lines_lit + ",\n                  \"\"])",
        out, count=1)
    # plik testowy + diff paths (w template rozbite na literaly: os.path.join, a/tests/, b/tests/)
    out = out.replace("test_top_lines.py", f["test_file"].split("/")[-1])
    # sandbox odpala WSZYSTKIE testy repo (stare + nowy) — regresje lapane przed POST
    # "==TESTFILE <name>==" delimuje sekcje per plik; night.py (W19 honest-fail gate)
    # orzeka cheating TYLKO w sekcji pliku testowego featury — nie w calym sklejonym
    # tests_out (lekcja z nocy 06/07.10: 58x marker z poprzednich plikow = falszywy alarm)
    out = out.replace('"cd {repo} && python3 tests/' + f["test_file"].split("/")[-1] + '"',
                      '"cd {repo} && for t in tests/test_*.py; do '
                      'echo \\"==TESTFILE $t==\\"; python3 $t || exit 1; done"')
    out = out.replace('"--- feat/top-lines\\n"', f'"--- {f["branch"]}\\n"')

    # Zadania typu "answer_path": blok odpowiedzi agenta trafia do innego
    # pliku niz src/lab/__init__.py (np. plik testowy); test_lines harnessu
    # zapisujemy jako bramke w osobnym pliku (nie trafia do patcha).
    ans = f.get("answer_path")
    if ans:
        gate = f.get("gate_file", "tests/test_zz_spec_gate.py")
        out = out.replace(
            'src_path = os.path.join(repo, "src", "lab", "__init__.py")',
            f'src_path = os.path.join(repo, "{ans}")')
        out = out.replace(
            'test_path = os.path.join(repo, "tests", "' + f["test_file"].split("/")[-1] + '")',
            f'test_path = os.path.join(repo, "{gate}")')
        out = out.replace(
            '"a/src/lab/__init__.py", "b/src/lab/__init__.py"',
            f'"a/{ans}", "b/{ans}"')
        out = out.replace(' + "".join(d2)', '')
    # Zadania typu "repair": test_file juz istnieje na main (RED by design).
    # Nie dolaczamy diffu "utworzenia" pliku testowego (d2) do patcha —
    # inaczej git apply --check failuje ("patch does not apply").
    if f.get("existing_test"):
        out = out.replace(' + "".join(d2)', '')
    # TWARDY GATE: env value (AX_TASK_YAML) ma limit 32768 znakow.
    # Render powyzej limitu = aktor nie powstanie (InvalidArgument z API,
    # nie widoczny w exit code ax apply!). Zatrzymujemy PRZED deployem.
    if len(out) > 32768:
        raise RuntimeError(
            f"GATE: rendered task {len(out)} B przekracza limit 32768 "
            "(env AX_TASK_YAML) — odchudzic spec/prompt/tail")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in FEATURES:
        print("usage: make_task.py <feature>", file=sys.stderr)
        print("features:", ", ".join(FEATURES), file=sys.stderr)
        sys.exit(2)
    out = render(sys.argv[1])
    dest = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/{sys.argv[1]}.template-out.yaml"
    open(dest, "w", encoding="utf-8").write(out)
    print(f"OK {dest} {len(out)} B; __GEMINI_KEY__ present: {'__GEMINI_KEY__' in out}; "
          f"__REPO_B64__ resolved: {'__REPO_B64__' not in out}; "
          f"providers unresolved: {sum(1 for p in ('__MODEL_PROVIDER__','__LLM_MODEL__','__LLM_BASE_URL__','__LLM_KEY__') if p in out)}")
