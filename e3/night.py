#!/usr/bin/env python3
"""E3 night runner: jeden feature jednej nocy (seryjnie, wg planu E3).

Sekwencja (wzorzec E2 + walidacja 01/10):
  0. preflight: quota Gemini OK? repo czyste? main aktualny?
  1. wybierz pierwszy NIEzrobiony feature z kolejki (specs/ = issues)
  2. make_task.render() -> template (z placeholderem __GEMINI_KEY__)
  3. scp template na serv2 -> iniekcja klucza server-side ->
     ax apply -> egress-policy (PEŁNA ŚCIEŻKA kubectl-ate) -> resume
  4. poll receivera (~/ax-test/data/lab-<feature>-*.json, mtime > start)
  5. dispatch.py payload -> PR -> merge
  6. cleanup: rendered YAML na serv2, task DELETE (nie suspend!)
  7. digest -> stdout (cron go odbiera i wysyła na TG)

Użycie: night.py [--feature slug] [--dry-run]
Exit:  0 = zmergowano; 1 = soft-fail (digest opisuje błąd); 2 = usage.
Klucz Gemini: WYŁĄCZNIE server-side z ~/ax-test/gemini-key.env (serv2).
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import FEATURES  # noqa: E402
import make_task  # noqa: E402

SERV2 = "hermes@100.65.215.34"
REMOTE_TPL = "/tmp/e3-night.template.yaml"
REMOTE_YAML = "/tmp/e3-night.rendered.yaml"
REMOTE_KEY = "/home/hermes/ax-test/gemini-key.env"
EGRESS_JSON = "/home/hermes/ax-test/lab-toplines1-egress.json"
DATA_DIR = "/home/hermes/ax-test/data"
KEY_LEN = 53  # format AQ.A… — walidacja po DŁUGOŚCI, nie prefiksie
POLL_TIMEOUT = 40 * 60  # task 3 s–13 min; zawieszone npm >30 min = zabite
POLL_STEP = 60

QUEUE = ["slug", "rolling", "titlecase",
         "word-counts", "chunk", "ngrams", "rle", "template", "parse-kv",  # poziomy 1-3 od 02/10
         "semver", "conventional-commit", "parse-duration",  # fala 2 L4 od 03/10
         "crontab-next", "changelog", "git-diff-stat", "git-log-json",  # fala 2 L5
         "env-lint", "parse-diff",  # fala 2 L6
         "expr-lex", "expr-parse", "expr-eval"]  # pipeline "testy dziennie" P1 (manual trigger)

# Safeguard quota Z.ai (plan E3 krok 4): 5h >= 85% -> skip nocy; weekly >= 90% -> pauza.
ZAI_ENV = os.path.expanduser("~/.hermes/profiles/ax-factory/.env")
ZAI_5H_SKIP = 85
ZAI_WEEKLY_PAUSE = 90

# Stan nocny (sloty 2x/noc od 03/10): feature z adnotacją z dzisiejszą datą
# nie jest brany ponownie tej nocy (niezależność slotów); porazka wroci nastepnej nocy.
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "night-state.json")


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def attempted_today() -> set[str]:
    """Features juz podjete dzis (dowolny slot, sukces czy porazka)."""
    try:
        st = json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return set()
    today = _today()
    return {f for f, d in st.items() if str(d).startswith(today)}


def mark_attempted(feature: str) -> None:
    st = {}
    try:
        st = json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    today = _today()
    for f in [k for k, v in st.items() if not str(v).startswith(today)]:
        del st[f]  # przycinaj stare dni
    st[feature] = today
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"), indent=1)


def zai_quota() -> tuple[int, int]:
    """(pct_5h, pct_weekly) z api.z.ai; (-1, -1) = brak klucza / błąd API."""
    key = ""
    for l in open(ZAI_ENV, encoding="utf-8"):
        if l.startswith("ZAI_API_KEY="):
            key = l.split("=", 1)[1].strip().strip('"\'')
    if not key:
        return -1, -1
    import urllib.request
    req = urllib.request.Request(
        "https://api.z.ai/api/monitor/usage/quota/limit",
        headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
    except Exception:  # noqa: BLE001
        return -1, -1
    p5 = wk = -1
    for lim in data.get("data", {}).get("limits", []):
        if lim.get("type") == "TOKENS_LIMIT":  # okno 5h (reset co 5h)
            p5 = int(lim.get("percentage") or 0)
        elif lim.get("type") == "TIME_LIMIT":  # cykl tygodniowy
            wk = int(lim.get("percentage") or 0)
    return p5, wk


def ssh(cmd: str, timeout: int = 120, check: bool = True):
    """Login-shell wrapper jest zbędny przy bash -lc; AX_SERVER w ~/.profile."""
    p = subprocess.run(["ssh", SERV2, cmd], capture_output=True, text=True,
                       timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"ssh failed ({p.returncode}): {cmd}\n"
                           f"stderr: {p.stderr[-400:]}")
    return p


def pick_feature(dry: bool) -> str | None:
    """Pierwszy feature, którego funkcji nie ma w src/lab/__init__.py."""
    init = open(os.path.join(make_task.REPO, "src/lab/__init__.py"),
                encoding="utf-8").read()
    skip = attempted_today()  # juz podjete dzisiejszej nocy (inny slot)
    for name in QUEUE:
        if name in skip:
            continue
        fn = FEATURES[name]["test_import"].split()[-1]
        if f"def {fn}(" not in init:
            return name
    return None


def preflight() -> list[str]:
    errs = []
    # Safeguard quota Z.ai NAJPIERW (plan E3 krok 4) — nie pal SSH/deplojów przy blokadzie
    # E3_SKIP_QUOTA=1 (env, tylko jawne ręczne runy): pomija próg 5h/weekly, ale NIE err API.
    if os.environ.get("E3_SKIP_QUOTA") == "1":
        p5, wk = zai_quota()
        if p5 < 0:
            errs.append("quota Z.ai: brak klucza / API err — fail-safe stop")
    else:
        p5, wk = zai_quota()
        if p5 < 0:
            errs.append("quota Z.ai: brak klucza / API err — fail-safe stop")
        elif p5 >= ZAI_5H_SKIP:
            errs.append(f"quota Z.ai 5h = {p5}% (>= {ZAI_5H_SKIP}%) — skip nocy")
        elif wk >= ZAI_WEEKLY_PAUSE:
            errs.append(f"quota Z.ai weekly = { wk }% (>= {ZAI_WEEKLY_PAUSE}%) — pauza do resetu")
    repo = make_task.REPO
    # dirty = tylko pliki, które git chce commitować (igonruje .gitignore'd)
    porcelain = subprocess.run(["git", "-C", repo, "status", "--porcelain"],
                               capture_output=True, text=True).stdout
    real = [l for l in porcelain.splitlines()
            if not l.strip().startswith("??") or "pycache" not in l]
    if real:
        errs.append(f"repo dirty: {real[:3]}")
    b = subprocess.run(["git", "-C", repo, "branch", "--show-current"],
                       capture_output=True, text=True).stdout.strip()
    if b != "main":
        errs.append(f"not on main (on {b})")
    subprocess.run(["git", "-C", repo, "pull", "-q", "--ff-only"],
                   check=True, capture_output=True)
    # quota Gemini: ping quoty na serv2 (wzorzec z E2 — exit 0 = OK)
    p = ssh("bash -lc 'set -a; source ~/ax-test/gemini-key.env; set +a; "
            "curl -s -o /dev/null -w \\\"%{http_code}\\\" "
            "https://generativelanguage.googleapis.com/v1beta/models "
            "-H \"x-goog-api-key: $GEMINI_API_KEY\"'", check=False)
    code = (p.stdout or "").strip().strip('"')
    if code != "200":
        errs.append(f"quota ping HTTP {code or 'ERR'} (stderr: {p.stderr[-120:]!r})")
    return errs


def deploy(task_yaml_local: str, task_name: str) -> None:
    # 0) tarball repo -> serv2 payloads/ (sandbox pobiera go GET /payload/repo.tar.gz;
    #    inline REPO_B64 łamał limit 32 KiB env/command w ActorTemplate)
    tar_local = f"/tmp/e3-{task_name}-repo.tar.gz"
    subprocess.run(["bash", "-c",
                    f"git -C {make_task.REPO} archive --format=tar.gz HEAD > {tar_local}"],
                   check=True)
    subprocess.run(["scp", "-q", tar_local,
                    f"{SERV2}:~/ax-test/payloads/repo.tar.gz"], check=True)
    # template (placeholder) -> serv2; klucz wstrzykiwany TYLKO tam
    subprocess.run(["scp", "-q", task_yaml_local, f"{SERV2}:{REMOTE_TPL}"],
                   check=True)
    # iniekcja server-side: podmień placeholder kluczem z env-file (mode 600)
    inject = (
        "python3 - <<'PYEOF'\n"
        "import os\n"
        f"key = [l.split('=',1)[1].strip().strip('\\\"\\'') for l in open('{REMOTE_KEY}') "
        "if 'GEMINI_API_KEY=' in l and not l.strip().startswith('#')][0]\n"
        "assert len(key) == 53, f'key len {len(key)} != 53'\n"
        f"t = open('{REMOTE_TPL}').read()\n"
        "assert '__GEMINI_KEY__' in t, 'placeholder missing'\n"
        f"open('{REMOTE_YAML}','w').write(t.replace('__GEMINI_KEY__', key))\n"
        f"print('RENDER_OK', os.path.getsize('{REMOTE_YAML}'))\n"
        "PYEOF"
    )
    ssh(f"chmod 600 {REMOTE_TPL} {REMOTE_YAML} 2>/dev/null; " + inject)
    # apply + egress (PEŁNA ŚCIEŻKA — sudo nie dziedziczy PATH) + resume
    # egress-policy: parent Actor moze nie istniec od razu po resume (race).
    # Retry do 12 prob co 10s; jesli actor istnieje, exit 0 i koniec petli.
    egress_retry = (
        "for i in $(seq 1 12); do sleep 10; "
        "if sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml "
        "/home/hermes/go/bin/kubectl-ate create egress-policy " + task_name +
        " -a default -f " + EGRESS_JSON + "; then EG=0; break; else EG=1; fi; "
        "done; [ \"$EG\" = \"0\" ] || exit 1"
    )
    deploy_cmd = (
        "bash -lc 'ax delete task " + task_name + " 2>/dev/null; "
        "ax apply -f " + REMOTE_YAML + " && "
        "ax resume task " + task_name + " && " + egress_retry + " && "
        "ax resume task " + task_name + "'"
    )
    ssh(deploy_cmd, timeout=600)


def wait_result(task_name: str, not_before: float) -> str:
    """Poll ~/ax-test/data/lab-<feature>-*.json z guardem not_before."""
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        p = ssh(f"ls -t {DATA_DIR}/{task_name}-*.json 2>/dev/null | head -1",
                check=False)
        newest = p.stdout.strip()
        if newest:
            st = ssh(f"stat -c %Y {newest!r}", check=False).stdout.strip()
            if st.isdigit() and int(st) >= int(not_before):
                local = f"/tmp/e3-{task_name}-payload.json"
                subprocess.run(["scp", "-q", f"{SERV2}:{newest}", local],
                               check=True)
                return local
        time.sleep(POLL_STEP)
    raise TimeoutError(f"no result file after {POLL_TIMEOUT}s for {task_name}")


def cleanup_serv2(task_name: str) -> None:
    """DELETE (nie suspend — auto-wznowienie pali quotę) + kasuj YAML z kluczem."""
    ssh(f"rm -f {REMOTE_TPL} {REMOTE_YAML}", check=False)
    ssh(f"bash -lc 'ax delete task {task_name}'", timeout=900, check=False)


def purge_old_results(task_name: str) -> None:
    """Usuń stare pliki wyników receivera przed deployem.

    Bez tego wait_result może złapać wynik POPRZEDNIEGO runu tego samego
    taska (mtime >= start runu, bo POST przyszedł już po starcie)."""
    ssh(f"rm -f {DATA_DIR}/{task_name}-*.json", check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    lines = ["[E3 night] " + time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())]

    if args.feature:
        feature = args.feature
    else:
        feature = pick_feature(True)
        if feature is None:
            lines.append("Kolejka pusta — wszystkie features już na main, "
                         "lub wszystkie podjęte dziś. Nic do roboty.")
            print("\n".join(lines))
            return 0

    errs = preflight()
    if errs:
        lines.append("PREFLIGHT FAIL: " + "; ".join(errs))
        print("\n".join(lines))
        return 1
    lines.append(f"preflight OK; feature: {feature}")

    task = f"lab-{feature}"
    if args.dry_run:
        lines.append("DRY-RUN: deploy pominięty; feature do wykonania: " + feature)
        print("\n".join(lines))
        return 0
    mark_attempted(feature)  # dopiero realna próba (dry-run nie zatruwa stanu)

    not_before = time.time() - 120
    try:
        local_tpl = "/tmp/e3-night-local.yaml"
        open(local_tpl, "w", encoding="utf-8").write(
            make_task.render(feature))
        lines.append(f"template OK ({os.path.getsize(local_tpl)} B, "
                     "placeholder __GEMINI_KEY__ zachowany)")
        purge_old_results(task)
        deploy(local_tpl, task)
        lines.append(f"deploy OK: {task} (apply+egress+resume)")
        payload = wait_result(task, not_before)
        data = json.load(open(payload, encoding="utf-8"))
        _patch = (data.get("results") or {}).get("patch") or data.get("patch") or ""
        lines.append(f"wynik odebrany: status={data.get('status')} "
                     f"patch={len(_patch)} B")
    except Exception as e:  # noqa: BLE001
        lines.append(f"FAIL: {type(e).__name__}: {e}")
        cleanup_serv2(task)
        print("\n".join(lines))
        return 1

    # dispatch -> PR -> merge
    d = subprocess.run([sys.executable,
                        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "dispatch.py"),
                        payload, feature],
                       capture_output=True, text=True)
    lines.append("dispatch rc=" + str(d.returncode))
    for l in (d.stdout + d.stderr).strip().splitlines():
        lines.append("  " + l)
    rc = 0 if d.returncode == 0 else 1
    lines.append(f"CLEANUP: " + task)
    cleanup_serv2(task)
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main())
