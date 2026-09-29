# ax-sentinel axrepo task — runs INSIDE the AX runner (python 3.12, git, no pyyaml).
# sentinel.py substitutes {{REPO_URL}}, {{REPO_SHA}}, {{REPO_DATE}}.
# The private repo tarball is served over Tailscale by sentinel.py (HTTP :18081
# on serv2uk) instead of being embedded — a 220 KB manifest broke actor
# creation ("actor template not found", see TESTING.md Run sentinel-1).

import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.request

REPO_URL = "{{REPO_URL}}"
REPO_SHA = "{{REPO_SHA}}"
REPO_DATE = "{{REPO_DATE}}"

SECRET_PATTERNS = [
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_\-]{20,}")),
    ("ax-internal-token", re.compile(r"AQ\.[A-Za-z0-9_\-]{20,}")),
    ("telegram-bot-token", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_\-]{30,}")),
    ("github-oauth", re.compile(r"\bgho_[A-Za-z0-9]{30,}")),
    ("github-pat", re.compile(r"\bghp_[A-Za-z0-9]{30,}")),
]

SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico",
                 ".pdf", ".zip", ".gz", ".tgz", ".mp3", ".mp4", ".pyc")


def _sh(cmd, cwd=None, timeout=120):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def fetch_repo():
    dest = "/tmp/repo.tgz"
    urllib.request.urlretrieve(REPO_URL, dest)
    rd = "/tmp/repo"
    os.makedirs(rd, exist_ok=True)
    with tarfile.open(dest, mode="r:gz") as tf:
        tf.extractall(rd)  # archive built by `git archive` on serv — trusted
    return rd


def run_offline_tests(repo):
    rc, out = _sh([sys.executable, "-m", "pip", "install", "--user", "--quiet",
                   "pyyaml"], timeout=180)
    pip_rc = rc
    cmd = [sys.executable, "axbot/tests/live/axbot_offline_tests.py"]
    env = dict(os.environ, PYTHONPATH="axbot/src")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                           cwd=repo, env=env)
        t_rc, t_out = p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        t_rc, t_out = 124, "timeout after 600s"
    tail = "\n".join(t_out.strip().splitlines()[-12:])
    m = re.search(r"(\d+) pass / (\d+) fail", tail)
    passed, total = (m.group(1), str(int(m.group(1)) + int(m.group(2)))) \
        if m else ("?", "?")
    return {"pip_rc": pip_rc, "test_rc": t_rc, "passed": passed,
            "total": total, "tail": tail}


def scan_secrets(repo):
    hits = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for fn in files:
            if fn.endswith(SKIP_SUFFIXES):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        for label, pat in SECRET_PATTERNS:
                            if pat.search(line):
                                rel = os.path.relpath(path, repo)
                                # redact: never ship the secret itself
                                hits.append(f"{rel}:{i} [{label}]")
            except OSError:
                pass
    return hits


tests = run_offline_tests(fetch_repo())
secrets = scan_secrets("/tmp/repo")

lines = []
lines.append(f"repo zero-dot7/AX @ {REPO_SHA[:9]} ({REPO_DATE})")
lines.append(f"offline tests: {tests['passed']}/{tests['total']} "
             f"(rc={tests['test_rc']})")
if tests["test_rc"] != 0:
    lines.append("test tail:\n" + tests["tail"])
lines.append(f"secret scan: {'CLEAN' if not secrets else str(len(secrets)) + ' HITS'}")
for h in secrets[:20]:
    lines.append("  " + h)

md = "\n".join(lines)
results = {"sha": REPO_SHA, "tests": tests, "secrets": secrets}

# --- ship the result -------------------------------------------------------
payload = json.dumps({"task": "sentinel-axrepo", "ts": time.time(),
                      "md": md, "results": results}).encode()
for i in range(4):
    try:
        req = urllib.request.Request("http://100.65.215.34:18080/",
                                     data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("post", resp.status, flush=True)
            break
    except Exception as e:
        print("retry", i + 1, repr(e), flush=True)
        time.sleep(4)
else:
    raise RuntimeError("receiver post failed")
print("DONE", flush=True)
