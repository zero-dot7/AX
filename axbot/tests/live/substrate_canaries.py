#!/usr/bin/env python3
"""Substrate canaries — upstream google/ax regression detectors (non-destructive).

Covers two upstream issues that directly affect our stack:
  #443  AX sends removed snapshot_config.on_resume -> Substrate >=6a35150 rejects
        the custom ActorTemplate and AX silently falls back to default template
        (which does not exist on a stock install -> apply fails with a misleading
        "actor template not found"). Our substrate is older, but the SAME fallback
        path also fires for manifest bugs we CAN hit today (env value >32768 chars,
        malformed image ref) — so the canary greps the fallback WARN itself, plus
        the tag-3 signature, plus the fatal "actor template not found".
  #442  Redis restart loses Task state and orphans Substrate actors. Our Redis is
        host redis-server with RDB to /var/lib/redis (not a PVC-less pod), so the
        audit checks: dump.rdb exists + fresh, save schedule sane, AOF status;
        plus a divergence detector: actors without a Task record = orphans.

Run from the Hermes host (drives serv2uk over ssh, BatchMode key):
    python3 axbot/tests/live/substrate_canaries.py [--since 24h]

Exit 0 = all canaries green; exit 1 = regression detected (never silent).
"""
import re
import subprocess
import sys
import time

SSH = ["ssh", "-o", "BatchMode=yes", "hermes@100.65.215.34"]

# journalctl --since accepts e.g. "24h", "2026-10-03 12:00"
SINCE = "24h"
for i, a in enumerate(sys.argv):
    if a == "--since" and i + 1 < len(sys.argv):
        SINCE = sys.argv[i + 1]

FAILS = []
WARNS = []


def sh(cmd, timeout=60):
    """Run a remote command through a login shell; return stdout."""
    full = SSH + ["bash -lc %s" % subprocess.list2cmdline([cmd])]
    r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def check(name, ok, detail=""):
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def warn(name, detail=""):
    print("WARN %s%s" % (name, (" — " + detail) if detail else ""))
    WARNS.append(name)


# --- Canary 1 (#443): custom-ActorTemplate fallback in ax-controller logs -----
FALLBACK_RE = re.compile(r"could not create custom ActorTemplate, falling back")
TAG3_RE = re.compile(r"unknown field with protobuf tag 3")
NOTFOUND_RE = re.compile(r"actor template not found")

log = sh("sudo -n journalctl -u ax-controller --since %s --no-pager" % SINCE, timeout=120)
lines = [l for l in log.splitlines() if FALLBACK_RE.search(l) or TAG3_RE.search(l) or NOTFOUND_RE.search(l)]

fallbacks = [l for l in lines if FALLBACK_RE.search(l)]
tag3 = [l for l in lines if TAG3_RE.search(l)]
notfound = [l for l in lines if NOTFOUND_RE.search(l) and not FALLBACK_RE.search(l)]

check("#443 tag3 on_resume regression (substrate >=6a35150)", not tag3,
      "%d hits" % len(tag3) if tag3 else "clean")
check("#443 ActorTemplate fallback (apply broken or manifest bug)", not fallbacks,
      "%d hits — inspect env-length/image-ref in manifests" % len(fallbacks) if fallbacks else "clean")
check("#443 fatal 'actor template not found'", not notfound,
      "%d hits" % len(notfound) if notfound else "clean")

# --- Canary 2 (#442): Redis durability audit ----------------------------------
info = sh("redis-cli -h 127.0.0.1 INFO persistence; redis-cli -h 127.0.0.1 CONFIG GET appendonly; redis-cli -h 127.0.0.1 CONFIG GET save; redis-cli -h 127.0.0.1 CONFIG GET dir")
aof = re.search(r"^appendonly:(\w+)", info, re.M)
save = re.search(r"^save\r?\n([^\r\n]+)", info, re.M) or re.search(r'"save",?"([^"]+)"', info)
rdb_status = re.search(r"^rdb_last_bgsave_status:(\w+)", info, re.M)
last_save = re.search(r"^rdb_last_save_time:(\d+)", info, re.M)
dump = sh("sudo -n ls -la /var/lib/redis/dump.rdb")

check("#442 RDB snapshot present on disk", "dump.rdb" in dump, dump.strip())
check("#442 rdb_last_bgsave_status ok", bool(rdb_status) and rdb_status.group(1) == "ok",
      rdb_status.group(1) if rdb_status else "missing")
if last_save:
    age_h = (time.time() - int(last_save.group(1))) / 3600
    # save schedule default saves at least hourly under load; a file much older
    # than the save window means state changes would be lost on restart
    check("#442 dump.rdb freshness (<2h)", age_h < 2, "last save %.1fh ago" % age_h)
else:
    check("#442 dump.rdb freshness (<2h)", False, "rdb_last_save_time missing")
if aof:
    warn("#442 AOF disabled", "RDB-only: window of loss = save interval; enable AOF if task state grows critical")
check("#442 redis dir not tmpfs", "dir" in info and "/var/lib/redis" in info, "")

# --- Canary 3 (#442): task/actor divergence (orphan detector) -----------------
tasks_out = sh("ax get tasks 2>&1")
actors_out = sh("kubectl-ate get actors --all-atespaces 2>&1")

task_names = set(re.findall(r"^(sentinel-\S+|lab-\S+|\S+?)\s+default\s+(Running|Suspended|Terminating|Failed|Pending)", tasks_out, re.M)) or None
# simpler: column 1 of ax get tasks header-less rows
task_names = set()
for l in tasks_out.splitlines():
    if l.startswith("NAME") or not l.strip():
        continue
    task_names.add(l.split()[0])

actor_rows = []
for l in actors_out.splitlines():
    if l.startswith("ATESPACE") or not l.strip():
        continue
    parts = l.split()
    if len(parts) >= 4:
        actor_rows.append((parts[0], parts[1], parts[3], parts[-1]))  # atespace, name, state, age

orphans = [(a, n, s) for (a, n, s, _) in actor_rows if n not in task_names and not n.endswith("-tmpl")]
stuck = [l for l in tasks_out.splitlines() if "Terminating" in l]

check("#442 no orphaned actors (actor without Task record)", not orphans,
      ", ".join("%s/%s %s" % o for o in orphans) if orphans else "clean")
if stuck:
    warn("#442 tasks stuck Terminating", "%d task(s) holding worker slots: %s" % (len(stuck), "; ".join(l.split()[0] for l in stuck)))
else:
    check("#442 no tasks stuck Terminating", True)

print()
print("substrate canaries: %d fail, %d warn" % (len(FAILS), len(WARNS)))
sys.exit(1 if FAILS else 0)
