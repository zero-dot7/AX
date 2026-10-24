#!/usr/bin/env python3
"""Substrate canaries — upstream google/ax regression detectors (non-destructive).

Covers upstream google/ax issues that directly affect our stack:
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
  #471  Task budgets (spec.budget: activeDeadline + maxTokens) and status.usage.
        Upstream DEFERRED (rakyll 2026-10-16: #485 removed UsageStats; budget
        spec waits for the next Task kind). Feature probe on the deployed ax
        binary: absence is EXPECTED today (WARN, informational); presence means
        an upgrade landed and we should verify enforcement E2E.
  #475  Credentials via egress injection (ate-secret:// URIs, replaceHeaders,
        SecretStore) — real keys never enter the sandbox. Upstream in design.
        Feature probe on the deployed controller/kubectl-ate binaries: absence
        expected (WARN); presence = start migrating secrets off spec.env.
  #498  Pre-bump guard for the Substrate v0.5.0 ActorTemplate break
        (sandbox_config field 6 removed, resources required, digest-pinned
        images). FAILs only if someone bumps ~/substrate past the proto change
        while our ax build still emits sandbox_config — exactly the state in
        which every Task apply would start failing with a misleading
        "actor template not found".

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
changes = re.search(r"^rdb_changes_since_last_save:(\d+)", info, re.M)
if last_save:
    age_h = (time.time() - int(last_save.group(1))) / 3600
    # save schedule default saves at least hourly under load; a file much older
    # than the save window means state changes would be lost on restart.
    # Idle exception: 0 unpersisted changes means on-disk RDB is already
    # current, so an old timestamp loses no state (false-positive guard).
    if changes and changes.group(1) == "0":
        check("#442 dump.rdb freshness (<2h)", True,
              "last save %.1fh ago but 0 changes since — RDB current (idle)" % age_h)
    else:
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


# --- Canary 4 (#471): task budgets / usage — feature probe on ax binaries ------
# spec.budget{activeDeadline,maxTokens} + status.usage. Deferred upstream after
# #485; expected absent in our v0.2-era build. Distinctive markers only:
# "TokenBudgetExceeded" (proposal phase 3) / "activeDeadline". NB maxTokens and
# secretRef-like generic names already exist via unrelated libs (verified
# 2026-10-19) and must not be used as markers.
ax_path = sh("command -v ax").strip().splitlines()
ax_path = ax_path[0] if ax_path else ""

_ctrl_bin = ""
def ctrl_bin_path():
    """Absolute path of the deployed ax-controller binary (systemd ExecStart)."""
    global _ctrl_bin
    if not _ctrl_bin:
        unit = sh("systemctl cat ax-controller 2>/dev/null | grep -E '^ExecStart' | head -1").strip()
        m = re.search(r"ExecStart=\S*?(/[\w/.-]*(?:controller|ax)[\w/.-]*)", unit)
        _ctrl_bin = m.group(1) if m else ""
    return _ctrl_bin

def binary_grep(path, pattern):
    """grep -a count of pattern in a binary file on the remote host."""
    if not path:
        return -1
    # NB: pattern contains '|'; sh() only quotes whitespace, so shell-quote
    # both args ourselves or bash pipelines the grep apart.
    q = lambda s: "'" + s.replace("'", "'\\''") + "'"
    out = sh("grep -a -c -E %s %s" % (q(pattern), q(path))).strip()
    m = re.match(r"^(\d+)$", out)
    return int(m.group(1)) if m else -1

budget_hits = max(binary_grep(ax_path, "TokenBudgetExceeded|activeDeadline"),
                  binary_grep(ctrl_bin_path(), "TokenBudgetExceeded|activeDeadline"))
# NB: "DeadlineExceeded" deliberately excluded — stock grpc/codes string in every
# Go binary. "maxTokens" excluded — pre-existing unrelated lib hit (2026-10-19).
if budget_hits < 0:
    warn("#471 budget probe inconclusive", "ax/ax-controller binaries not found")
elif budget_hits == 0:
    warn("#471 spec.budget not in deployed ax", "expected: deferred upstream after #485; revisit on next ax bump (issue #471)")
else:
    check("#471 spec.budget present in ax build", True,
          "%d grep hits — verify enforcement E2E (deadline stop, usage in status) before relying on it" % budget_hits)

# --- Canary 5 (#475): egress credential injection — feature probe --------------
# Substrate side: ate-secret:// credentialUri + replaceHeaders in egress policy;
# AX side: SecretStore resource. Upstream in design. Markers chosen so that
# today's build greps 0 (generic "credentialUri"/"secretRef" fields already
# exist in substrate via unrelated features — verified 2026-10-19).
kt_path = sh("command -v kubectl-ate").strip().splitlines()
kt_path = kt_path[0] if kt_path else ""
cred_marks = "ate-secret://|replaceHeaders|SecretStore"
cred_hits = max(binary_grep(ctrl_bin_path(), cred_marks),
                binary_grep(kt_path, cred_marks),
                binary_grep(ax_path, cred_marks))
if cred_hits == 0:
    warn("#475 egress credential injection absent", "expected: design-stage upstream (generic credentialUri field in substrate predates #475); secrets still in task env — keep axbot digest pin + env hygiene")
elif cred_hits < 0:
    warn("#475 credential probe inconclusive", "controller/kubectl-ate binaries not locatable")
else:
    check("#475 credential injection present in deployed stack", True,
          "start migrating keys off spec.env to SecretStore + egress replaceHeaders (issue #475, cf. giantswarm/substrate-credential-providers)")

# --- Canary 6 (#498): pre-bump guard — Substrate v0.5.0 ActorTemplate break ----
# Break condition: ~/substrate proto no longer declares sandbox_config while the
# deployed ax-controller still emits it. NB the ax CLI carries no sandboxConfig
# strings (verified 2026-10-19) — the controller builds the ActorTemplate, so it
# is the binary to watch. v0.5.0 release itself still HAS the field (#484); the
# removal lands in substrate >=3d3b929.
sub_ver = sh("git -C $HOME/substrate describe --tags --always 2>/dev/null").strip() or "unknown"
proto_has_sc = sh("grep -c sandbox_config $HOME/substrate/pkg/proto/ateapipb/ateapi.proto 2>/dev/null").strip()
proto_has_sc = bool(re.match(r"^[1-9]\d*$", proto_has_sc))
ax_has_sc = binary_grep(ctrl_bin_path(), "andbox_config|andboxConfig") > 0
digest_ok = binary_grep(ctrl_bin_path(), "@sha256:")

if not proto_has_sc:
    if ax_has_sc:
        check("#498 substrate/ax ActorTemplate compatibility", False,
              "substrate %s dropped sandbox_config but ax-controller still emits it — EVERY task apply will fail (#498); halt: drop SandboxConfig, set Resources, digest-pin images (cf. gethamster/ax 43fd8d5)" % sub_ver)
    else:
        warn("#498 substrate past ActorTemplate break", "substrate %s dropped sandbox_config; ax-controller no longer emits it — confirm digest-pinned runner image before resuming" % sub_ver)
else:
    check("#498 substrate pre-v0.5 ActorTemplate break (sandbox_config intact)", True,
          "substrate %s; controller%s emits sandboxConfig; digest-pinned image refs in controller: %s" % (sub_ver, "" if ax_has_sc else " does not", digest_ok if digest_ok >= 0 else "?"))

print()
print("substrate canaries: %d fail, %d warn" % (len(FAILS), len(WARNS)))
sys.exit(1 if FAILS else 0)
