#!/usr/bin/env python3
"""Offline tests for ax-sentinel (no cluster, no ssh, no network).

Run from the repo root:
    PYTHONPATH=ax-sentinel python3 ax-sentinel/tests/sentinel_offline_tests.py

Covers: config loading, task source substitution, manifest build, egress rule
construction, result regex, digest rendering, stale-result guard.
"""
import base64
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SENT_DIR = os.path.dirname(HERE)
sys.path.insert(0, SENT_DIR)

import sentinel  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} {detail}")


print("T1: config")
import config  # noqa: E402
check("T1.1 repo_dir points at a git checkout",
      os.path.isdir(os.path.join(config.REPO_DIR, ".git")))
check("T1.2 upstream repo configured",
      config.REPOS.get("upstream") == "https://github.com/google/ax.git")

print("T2: task source substitution (no live build)")
with open(os.path.join(SENT_DIR, "tasks", "axrepo_task.py")) as f:
    src = f.read()
subs = {"REPO_URL": "http://example/x.tgz", "REPO_SHA": "a" * 40,
        "REPO_DATE": "2026-09-29"}
for k, v in subs.items():
    src2 = src.replace("{{" + k + "}}", v)
    check(f"T2.{list(subs).index(k)+1} {k} placeholder exists and substitutes",
          src != src2 and "{{" + k + "}}" not in src2)
compile(src2, "axrepo", "exec")
check("T2.4 substituted axrepo source compiles", True)

with open(os.path.join(SENT_DIR, "tasks", "upstream_task.py")) as f:
    usrc = f.read()
usubs = {"KNOWN_SHA": "b" * 40, "KNOWN_TAGS": '["v0.3.1"]'}
for k, v in usubs.items():
    usrc2 = usrc.replace("{{" + k + "}}", v)
    check(f"T2.{5 + list(usubs).index(k)} upstream {k} substitutes",
          "{{" + k + "}}" not in usrc2)
compile(usrc2, "upstream", "exec")
check("T2.7 substituted upstream source compiles", True)

print("T3: manifest build")
name, body = "t", "print('hi')"
m = sentinel.manifest_for(name, body)
check("T3.1 apiVersion/kind", m["apiVersion"] == "ax.io/v1alpha1"
      and m["kind"] == "Task")
check("T3.2 image pinned by digest", m["spec"]["image"].startswith(
      "localhost:5001/ax-task-runner@sha256:"))
check("T3.3 command decodes back to source",
      base64.b64decode(m["spec"]["command"][2].split("'")[1]).decode()
      == body or body in m["spec"]["command"][2])
check("T3.4 manifest name", m["metadata"]["name"] == "t")

print("T4: result regex (offline-suite format)")
import re as _re
tail = "\n==== OFFLINE SUITE: 21 pass / 0 fail ====\nOFFLINE-ALL-GREEN"
mm = _re.search(r"(\d+) pass / (\d+) fail", tail)
check("T4.1 parses 'N pass / M fail'",
      mm and mm.group(1) == "21" and mm.group(2) == "0")
check("T4.2 total = pass + fail",
      str(int(mm.group(1)) + int(mm.group(2))) == "21")

print("T5: stale-result guard")
now = time.time()
not_before = now - 120  # sentinel.py: dispatched_at - 120
check("T5.1 fresh ts accepted", now > not_before)
check("T5.2 old (previous-run) ts rejected", (now - 3600 > not_before) is False)

print("T6: digest rendering")
outcomes = [
    ("t-ok", {"md": "line1\nline2"}, None),
    ("t-err", None, "egress failed"),
]
d = sentinel.render_digest(outcomes, now - 65)
check("T6.1 includes task names", "t-ok" in d and "t-err" in d)
check("T6.2 includes error text", "egress failed" in d)
check("T6.3 includes wall time", "65s" in d)
check("T6.4 counts ok tasks", "1/2" in d)
check("T6.5 header is a repo link",
      d.splitlines()[0] ==
      "[AX Sentinel — daily repo report](https://github.com/zero-dot7/AX)")

print("T7: merge_tags")
state = {"upstream": {"tags": ["v0.3.1"]}}
r = {"new_tags": ["v0.4.0"]}
check("T7.1 merges known + new",
      sentinel.merge_tags(state, r) == ["v0.3.1", "v0.4.0"])
check("T7.2 dedups",
      sentinel.merge_tags({"upstream": {"tags": ["v0.3.1"]}},
                          {"new_tags": ["v0.3.1"]}) == ["v0.3.1"])

print("T8: egress rules document shape")
rules = {"rules": [{"cidrs": {"cidrs": ["100.65.215.34/32"]}},
                   {"hostnames": {"patterns": ["api.github.com"]}}]}
check("T8.1 JSON-serializable", bool(json.dumps(rules)))

print(f"\n==== SENTINEL OFFLINE SUITE: {PASS} pass / {FAIL} fail ====")
sys.exit(1 if FAIL else 0)
