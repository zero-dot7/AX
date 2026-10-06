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

QUEUE = ["slug", "rolling", "titlecase"]  # kolejkowanie wg planu E3


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
    for name in QUEUE:
        fn = FEATURES[name]["test_import"].split()[-1]  # "from lab import slug"
        if f"def {fn}(" not in init:
            return name
    return None


def preflight() -> list[str]:
    errs = []
    repo = make_task.REPO
    if subprocess.run(["git", "-C", repo, "status", "--porcelain"],
                      capture_output=True).stdout.strip():
        errs.append("repo dirty")
    b = subprocess.run(["git", "-C", repo, "branch", "--show-current"],
                       capture_output=True, text=True).stdout.strip()
    if b != "main":
        errs.append(f"not on main (on {b})")
    subprocess.run(["git", "-C", repo, "pull", "-q", "--ff-only"],
                   check=True, capture_output=True)
    # quota Gemini: ping quoty na serv2 (wzorzec z E2 — exit 0 = OK)
    p = ssh("bash -lc 'source ~/ax-test/gemini-key.env 2>/dev/null; "
            "curl -s -o /dev/null -w \"%{http_code}\" "
            "https://generativelanguage.googleapis.com/v1beta/models "
            "-H \"Authorization: Bearer $GEMINI_API_KEY\"'", check=False)
    code = (p.stdout or "").strip()
    if code != "200":
        errs.append(f"gemini quota ping HTTP {code or 'ERR'} (stderr: "
                    f"{p.stderr[-120:]!r})")
    return errs


def deploy(task_yaml_local: str, task_name: str) -> None:
    # template (placeholder) -> serv2; klucz wstrzykiwany TYLKO tam
    subprocess.run(["scp", "-q", task_yaml_local, f"{SERV2}:{REMOTE_TPL}"],
                   check=True)
    # iniekcja server-side: podmień placeholder kluczem z env-file (mode 600)
    inject = (
        "python3 - <<'PYEOF'\n"
        "import os\n"
        f"key = [l.split('=',1)[1].strip().strip('\"\\'') for l in open('{REMOTE_KEY}') "
        "if l.strip().startswith('GEMINI_API_KEY')][0]\n"
        "assert len(key) == 53, f'key len {len(key)} != 53'\n"
        f"t = open('{REMOTE_TPL}').read()\n"
        "assert '__GEMINI_KEY__' in t, 'placeholder missing'\n"
        f"open('{REMOTE_YAML}','w').write(t.replace('__GEMINI_KEY__', key))\n"
        "print('RENDER_OK', os.path.getsize('{REMOTE_YAML}'))\n"
        "PYEOF"
    )
    ssh(f"chmod 600 {REMOTE_TPL} {REMOTE_YAML} 2>/dev/null; " + inject)
    # apply + egress (PEŁNA ŚCIEŻKA — sudo nie dziedziczy PATH) + resume
    deploy_cmd = (
        "bash -lc 'ax delete task " + task_name + " 2>/dev/null; "
        "ax apply -f " + REMOTE_YAML + " && "
        "ax resume task " + task_name + " && sleep 5 && "
        "sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml "
        "/home/hermes/go/bin/kubectl-ate create egress-policy " + task_name +
        " -a default -f " + EGRESS_JSON + " && "
        "ax resume task " + task_name + "'"
    )
    ssh(deploy_cmd, timeout=300)


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


def main() -> int:
    print("MAIN-ENTER", flush=True)
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
            lines.append("Kolejka pusta — wszystkie features już na main. Nic do roboty.")
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

    not_before = time.time() - 120
    try:
        local_tpl = "/tmp/e3-night-local.yaml"
        open(local_tpl, "w", encoding="utf-8").write(
            make_task.render(feature))
        lines.append(f"template OK ({os.path.getsize(local_tpl)} B, "
                     "placeholder __GEMINI_KEY__ zachowany)")
        deploy(local_tpl, task)
        lines.append(f"deploy OK: {task} (apply+egress+resume)")
        payload = wait_result(task, not_before)
        data = json.load(open(payload, encoding="utf-8"))
        lines.append(f"wynik odebrany: status={data.get('status')} "
                     f"patch={len((data.get('results') or {}).get('patch') or '')} B")
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


if __name__ == "__main":
    sys.exit(main())
