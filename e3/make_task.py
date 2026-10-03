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


def make_tarball_b64(repo: str) -> str:
    """Świeży tarball repo (git archive HEAD = main, bez .git)."""
    import subprocess
    p = subprocess.run(["git", "archive", "--format=tar.gz", "HEAD"],
                       cwd=repo, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("git archive failed: " + p.stderr.decode()[:200])
    return base64.b64encode(p.stdout).decode()


def render(feature_name: str, repo: str = REPO) -> str:
    f = FEATURES[feature_name]
    spec_path = os.path.join(repo, f["spec_file"])
    spec = open(spec_path, encoding="utf-8").read()

    prompt = PROMPT_HEAD + f["prompt_core"] + PROMPT_TAIL.format(
        spec=spec,
        existing=open(os.path.join(repo, "src/lab/__init__.py"),
                      encoding="utf-8").read(),
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
    out = out.replace('"cd {repo} && python3 tests/' + f["test_file"].split("/")[-1] + '"',
                      '"cd {repo} && for t in tests/test_*.py; do python3 $t || exit 1; done"')
    out = out.replace('"--- feat/top-lines\\n"', f'"--- {f["branch"]}\\n"')
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
          f"__REPO_B64__ resolved: {'__REPO_B64__' not in out}")
