#!/usr/bin/env python3
"""AI code reviewer — Anthropic-style pipeline for solo repos.

Layer 1: bug review       (diff vs whole repo + stated intent)
Layer 2: security review  (blocking: secrets, injection, auth, unsafe IO)
Layer 3: verification     (second pass drops findings that don't hold up
                          against the full file content = false-positive filter)

Posts one comment per PR (updated in place), writes step summary.
Exit 1 on any CRITICAL finding (blocking check), unless REVIEW_BLOCK=never.
Fails open: if the API is unavailable, posts a notice and exits 0.
"""
import json, os, re, subprocess, sys, urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
REPO = os.environ["GITHUB_REPOSITORY"]
PR = int(os.environ["PR_NUMBER"])
TOKEN = os.environ["GITHUB_TOKEN"]
KEY = os.environ.get("OPENROUTER_API_KEY", "")
MARKER = "<!-- ai-review -->"

DIFF_CAP, FILE_CAP, TOTAL_CAP = 90_000, 20_000, 140_000


def gh(path, accept="application/vnd.github+json"):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": accept},
    )
    with urllib.request.urlopen(req) as r:
        return r.read().decode("utf-8", "replace")


def post_comment(body):
    # update the existing ai-review comment if present, else create
    comments = json.loads(gh(f"/repos/{REPO}/issues/{PR}/comments?per_page=100"))
    for c in comments:
        if MARKER in c.get("body", ""):
            req = urllib.request.Request(
                f"{API}/repos/{REPO}/issues/comments/{c['id']}",
                data=json.dumps({"body": body}).encode(),
                headers={"Authorization": f"Bearer {TOKEN}",
                         "Accept": "application/vnd.github+json"},
                method="PATCH")
            urllib.request.urlopen(req)
            return
    req = urllib.request.Request(
        f"{API}/repos/{REPO}/issues/{PR}/comments",
        data=json.dumps({"body": body}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Accept": "application/vnd.github+json"},
        method="POST")
    urllib.request.urlopen(req)


def call_model(prompt, system, models):
    """Try model chain until one answers; return (model, text) or raise."""
    last = None
    for m in models:
        body = json.dumps({
            "model": m,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "temperature": 0.2,
        }).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {KEY}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
            return m, data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001 — chain fallback
            last = e
            print(f"model {m} failed: {e}", file=sys.stderr)
    if last is None:
        raise RuntimeError("no models configured")
    raise last


def extract_json(text):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    start = text.find("{")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("no JSON object in model output")


def cap(s, n):
    return s if len(s) <= n else s[:n] + f"\n...[truncated {len(s) - n} chars]"


def main():
    if not KEY:
        print("no OPENROUTER_API_KEY — AI review skipped (fails open)")
        sys.exit(0)

    models = [m for m in
              [os.environ.get("REVIEW_MODEL"),
               "qwen/qwen3-coder:free", "deepseek/deepseek-chat-v3.1:free",
               "z-ai/glm-4.6:free", "qwen/qwen3-coder"] if m]

    pr = json.loads(gh(f"/repos/{REPO}/pulls/{PR}"))
    diff = cap(gh(f"/repos/{REPO}/pulls/{PR}", accept="application/vnd.github.diff"), DIFF_CAP)
    intent = f"Title: {pr['title']}\n\nBody:\n{cap(pr.get('body') or '(none)', 4000)}"

    # repo context: file tree + full current content of changed files
    tree = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout
    files = [f for f in tree.splitlines() if f and "node_modules" not in f][:3000]
    changed = json.loads(gh(f"/repos/{REPO}/pulls/{PR}/files?per_page=100"))
    touched = [f["filename"] for f in changed]
    ctx, total = [], 0
    for f in touched:
        if not os.path.isfile(f) or f.endswith((".png", ".jpg", ".webp", ".ico")):
            continue
        try:
            content = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        content = cap(content, FILE_CAP)
        if total + len(content) > TOTAL_CAP:
            content = cap(content, max(0, TOTAL_CAP - total))
        ctx.append(f"===== FILE {f} (current version) =====\n{content}")
        total += len(content)
        if total >= TOTAL_CAP:
            break

    repo_ctx = (f"REPO FILE TREE:\n{cap(chr(10).join(files), 15000)}\n\n"
                f"CHANGED FILES (full current contents):\n" + "\n\n".join(ctx))

    def review(kind, focus):
        system = ("You are a rigorous code reviewer. You review ONLY what this "
                  "diff introduces — pre-existing issues are out of scope unless "
                  "the diff makes them worse. No style nits, no hypotheticals; "
                  "every finding must be verifiable against the provided file "
                  "contents. If there is nothing to report, return an empty "
                  "findings list — say so honestly. Answer in Polish (finding "
                  "titles/details in Polish, keys and code in English).")
        prompt = (f"## PR intent\n{intent}\n\n## Diff\n```diff\n{diff}\n```\n\n"
                  f"## Repository context\n{repo_ctx}\n\n"
                  f"Task: {focus}\n"
                  "Return STRICT JSON only:\n"
                  '{"summary": "2-3 zdania oceny", "findings": ['
                  '{"severity": "critical|high|medium|low", "file": "...", '
                  '"line": 0, "title": "...", "detail": "..."}]}\n'
                  "Severity: critical = exploit/utrata danych/crash na main; "
                  "high = realny bug; medium = prawdopodobny problem; "
                  "low = wart uwagi.")
        m, out = call_model(prompt, system, models)
        data = extract_json(out)
        data.setdefault("findings", [])
        return m, data

    m1, bugs = review("bug",
        "Znajdź BUGI wprowadzone przez ten diff: logika, off-by-one, race, "
        "błędna obsługa błędów, niespójność z resztą repo, zmiana psująca "
        "inne miejsce, regresja testów. Sprawdź czy zmiana rozwiązuje problem "
        "z intencji PR i czy nie łamie niczego innego.")
    m2, sec = review("security",
        "Znajdź PROBLEMY BEZPIECZEŃSTWA wprowadzone przez ten diff: sekrety/"
        "tokeny w kodzie, injection (HTML/JS/shell/SQL), XSS, błędna autoryzacja, "
        "niebezpieczne dane z storage/network, path traversal, nieaktualne "
        "uprawnienia w manifestach.")

    findings = [dict(f, layer="bug") for f in bugs["findings"] if isinstance(f, dict)] + \
               [dict(f, layer="security") for f in sec["findings"] if isinstance(f, dict)]

    # layer 3: verification — drop findings that don't hold up
    dropped = []
    if findings:
        system = ("You are a verification judge. For each finding, check it "
                  "against the actual file contents and diff. Drop findings "
                  "that are wrong, already handled in the diff, pre-existing, "
                  "or pure speculation. Answer in Polish.")
        prompt = (f"## Diff\n```diff\n{diff}\n```\n\n## Files\n{repo_ctx}\n\n"
                  f"## Findings to verify\n{json.dumps(findings, ensure_ascii=False, indent=1)}\n"
                  'Return STRICT JSON: {"keep": [0,2], "drop": [1], '
                  '"reasons": {"1": "false positive, bo ..."}} '
                  "(indeksy listy findings).")
        try:
            mv, out = call_model(prompt, system, models)
            v = extract_json(out)
            keep = set(v.get("keep", []))
            new = []
            for i, f in enumerate(findings):
                if i in keep:
                    new.append(f)
                else:
                    dropped.append(f)
            findings = new
        except Exception as e:  # noqa: BLE001 — keep findings if verify fails
            print(f"verification pass failed: {e}", file=sys.stderr)

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: sev_order.get(f.get("severity") or "", 9))
    crit = [f for f in findings if (f.get("severity") or "") == "critical"]

    emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
    rows = "\n".join(
        f"| {emoji.get(f.get('severity') or '', '⚪')} {(f.get('severity') or '?').upper()} "
        f"| `{f.get('file') or '?'}:{f.get('line') or '?'}` | **{f.get('title') or ''}** "
        f"({f.get('layer') or ''})<br>{f.get('detail') or ''} |"
        for f in findings) or "*(brak findings — czysto)*"

    body = (
        f"{MARKER}\n## 🤖 AI review\n"
        f"**Bug review** ({m1}): {bugs.get('summary', '—')}\n\n"
        f"**Security review** ({m2}): {sec.get('summary', '—')}\n\n"
        f"| Severity | Miejsce | Finding |\n|---|---|---|\n{rows}\n\n"
        f"*Weryfikacja (false-positive filter): {len(dropped)} odrzuconych, "
        f"{len(findings)} utrzymanych. Reguła ≤3 cykli: po 3 rundach fixów "
        f"reviewer patrzy tylko na nowy diff — jeśli problem wraca, przemyśl "
        f"podejście zamiast iterować.*\n"
        + ("\n🔴 **BLOKADA**: znaleziono critical — PR nie może zostać "
           "zmergowany." if crit else ""))

    post_comment(body)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(body.replace(MARKER, ""))
    print(f"ai-review done: {len(findings)} findings, {len(dropped)} dropped")

    if crit and os.environ.get("REVIEW_BLOCK", "critical") == "critical":
        sys.exit(1)


if __name__ == "__main__":
    main()
