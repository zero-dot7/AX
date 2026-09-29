# ax-sentinel upstream task — runs INSIDE the AX runner.
# Checks google/ax upstream for new commits/tags since the last known state.
# sentinel.py substitutes {{KNOWN_SHA}}, {{KNOWN_TAGS}} before dispatch.

import json
import re
import subprocess
import time
import urllib.request

KNOWN_SHA = "{{KNOWN_SHA}}"
KNOWN_TAGS = json.loads('{{KNOWN_TAGS}}')  # e.g. ["v0.3.1"]

UPSTREAM = "https://github.com/google/ax.git"


def _sh(cmd, timeout=60):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def ls_remote():
    rc, out = _sh(["git", "ls-remote", UPSTREAM])
    if rc != 0:
        return None, out
    head = tags = None
    for ln in out.splitlines():
        sha, ref = ln.split("\t", 1)
        if ref == "refs/heads/main":
            main_sha = sha
        elif ref.startswith("refs/tags/") and not ref.endswith("^{}"):
            tags = (tags or []) + [ref[len("refs/tags/"):]]
    return {"main_sha": main_sha, "tags": tags or []}, out


info, raw = ls_remote()
lines = []
if info is None:
    lines.append("upstream check FAILED:")
    lines.append(raw[-500:])
    results = {"error": raw[-500:]}
else:
    new_tags = [t for t in info["tags"] if t not in KNOWN_TAGS]
    behind = "unknown"
    try:
        rc, out = _sh(["git", "ls-remote", UPSTREAM, "refs/heads/main"])
        # commit count via GitHub API (no clone): compare endpoint
        req = urllib.request.Request(
            "https://api.github.com/repos/google/ax/compare/"
            f"{KNOWN_SHA}...{info['main_sha']}",
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "ax-sentinel"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            cmp_data = json.load(resp)
        behind = cmp_data.get("ahead_by", "unknown")
        commits = [{"sha": c["sha"][:9],
                    "msg": (c["commit"]["message"] or "").splitlines()[0][:80]}
                   for c in cmp_data.get("commits", [])[:10]]
    except Exception as e:
        commits = [{"sha": "?", "msg": f"compare failed: {e!r}"}]
    lines.append(f"upstream google/ax main @ {info['main_sha'][:9]}")
    lines.append(f"known: {KNOWN_SHA[:9]} → behind by {behind} commits")
    if new_tags:
        lines.append(f"NEW TAGS: {', '.join(new_tags)}")
    else:
        lines.append("no new tags")
    for c in commits:
        lines.append(f"  {c['sha']} {c['msg']}")
    results = {"main_sha": info["main_sha"], "behind": behind,
               "new_tags": new_tags, "commits": commits}

md = "\n".join(lines)
payload = json.dumps({"task": "sentinel-upstream", "ts": time.time(),
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
        print("retry", i + 1, repr(e))
        time.sleep(4)
else:
    raise RuntimeError("receiver post failed")
print("DONE", flush=True)
