"""config.py — loads config.yaml with a minimal parser (no pyyaml dependency
on serv; stdlib only). Supports the flat two-key schema used here."""
import re

REPO_DIR = "/tmp/priv"
REPOS = {"upstream": "https://github.com/google/ax.git"}


def _load():
    global REPO_DIR, REPOS
    try:
        with open(__file__.replace("config.py", "config.yaml")) as f:
            text = f.read()
    except OSError:
        return
    m = re.search(r"^repo_dir:\s*(\S+)", text, re.M)
    if m:
        REPO_DIR = m.group(1)
    repos = {}
    in_repos = False
    for ln in text.splitlines():
        if re.match(r"^repos:\s*$", ln):
            in_repos = True
            continue
        if in_repos:
            m = re.match(r"^\s{2}([A-Za-z0-9_\-]+):\s*(\S+)", ln)
            if m:
                repos[m.group(1)] = m.group(2)
            elif ln.strip() and not ln.startswith("#"):
                break
    if repos:
        REPOS = repos


_load()
