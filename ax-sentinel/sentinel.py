#!/usr/bin/env python3
"""ax-sentinel — cross-server repo sentinel: dispatch from serv to AX on serv2uk.

Runs on serv (100.118.55.1). For each entry in config.yaml:
  1. builds an AX Task manifest (task source from tasks/*.py, substituted),
  2. ships it to serv2uk via scp, applies + egress + resumes via ssh,
  3. polls the receiver (100.65.215.34:18080) for the result JSON,
  4. writes results to state/ and renders a text digest.

Usage:
    python3 sentinel.py run            # dispatch all + wait + digest
    python3 sentinel.py digest         # re-render digest from last state
    python3 sentinel.py status         # show AX tasks state
"""
import base64
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import config  # noqa: E402  (config.py generated from config.yaml)

SERV2 = "hermes@100.65.215.34"
RECEIVER_POLL_CMD = (
    "ssh -o BatchMode=yes " + SERV2 +
    " 'cat ~/ax-test/data/{name}-*.json 2>/dev/null | tail -1'"
)
RUNNER_IMAGE = ("localhost:5001/ax-task-runner@"
                "sha256:594e20cb3e23a5961cf6c7c9cb40e06e670e43a2172534d17eccbf65f8b1ff94")
POLL_INTERVAL = 20
POLL_TIMEOUT = 1800  # 30 min per task — pip install alone takes ~15 min in the sandbox


def ssh(cmd, timeout=90):
    full = ["ssh", "-o", "BatchMode=yes", SERV2, "bash -lc " +
            json.dumps(cmd)]
    p = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def scp_up(local, remote):
    p = subprocess.run(["scp", "-q", local, SERV2 + ":" + remote],
                       capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def apply_egress(actor, hosts, cidrs):
    """Idempotent egress policy: delete + create (same as axbot kube.py)."""
    rules = []
    for c in cidrs:
        rules.append({"cidrs": {"cidrs": [c]}})
    for h in hosts:
        rules.append({"hostnames": {"patterns": [h]}})
    doc = {"rules": rules}
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(doc, fh)
    scp_up(path, "/tmp/egress-" + actor + ".json")
    os.unlink(path)
    ssh(f"kubectl-ate delete egress-policy {actor} -a default")
    rc, out = ssh(f"kubectl-ate create egress-policy {actor} -a "
                  f"default -f /tmp/egress-{actor}.json")
    return rc == 0, out


def render_task(name, source_path, subs):
    with open(source_path) as f:
        src = f.read()
    for k, v in subs.items():
        src = src.replace("{{" + k + "}}", v)
    return name, src


def build_axrepo_task(repo_dir):
    """HTTP-served repo task: git archive HEAD → upload to serv2uk files/ →
    task downloads it at runtime. (A 220 KB embedded manifest broke actor
    creation — 'actor template not found' — so we keep manifests small.)"""
    p = subprocess.run(["git", "-C", repo_dir, "archive", "HEAD"],
                       capture_output=True, timeout=120)
    if p.returncode != 0:
        raise RuntimeError("git archive failed: " + p.stderr.decode()[:300])
    sha = subprocess.run(["git", "-C", repo_dir, "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    date = subprocess.run(["git", "-C", repo_dir, "log", "-1", "--format=%cs", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    import gzip
    tgz_path = os.path.join(HERE, "out", "repo-head.tgz")
    os.makedirs(os.path.dirname(tgz_path), exist_ok=True)
    with open(tgz_path, "wb") as f:
        f.write(gzip.compress(p.stdout))
    remote = "~/ax-sentinel/files/repo-head.tgz"
    rc, err = scp_up(tgz_path, remote)
    if rc != 0:
        raise RuntimeError("repo upload failed: " + err)
    subs = {"REPO_URL": "http://100.65.215.34:18081/repo-head.tgz",
            "REPO_SHA": sha, "REPO_DATE": date}
    return render_task("sentinel-axrepo",
                       os.path.join(HERE, "tasks", "axrepo_task.py"), subs)


def build_upstream_task(state):
    last = state.get("upstream", {})
    subs = {
        "KNOWN_SHA": last.get("main_sha",
                              "e70162a34037c221fe6fadefd98308c05a4ad8f3"),
        "KNOWN_TAGS": json.dumps(last.get("tags", ["v0.3.1"])),
    }
    return render_task("sentinel-upstream",
                       os.path.join(HERE, "tasks", "upstream_task.py"), subs)


def manifest_for(name, body_src):
    # command must be a single python -c invocation; embed source as base64
    # to keep the YAML manifest small and quoting-proof
    b64 = base64.b64encode(body_src.encode()).decode()
    wrapper = (
        "import base64; exec(compile(base64.b64decode('" + b64 + "'), "
        "'task', 'exec'))"
    )
    return {
        "apiVersion": "ax.io/v1alpha1",
        "kind": "Task",
        "metadata": {"name": name, "atespace": "default"},
        "spec": {"image": RUNNER_IMAGE, "command": ["python3", "-c", wrapper]},
    }


def dispatch(name, manifest, hosts, cidrs):
    import yaml
    path = os.path.join(HERE, "out", name + ".yaml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True)
    with open(path, "w") as f:
        f.write(text)
    rc, err = scp_up(path, "/tmp/" + name + ".yaml")
    if rc != 0:
        return False, "scp failed: " + err
    rc, out = ssh(f"ax apply -f /tmp/{name}.yaml")
    if rc != 0 and "already exists" in out and "immutable" in out:
        ssh(f"ax delete task {name}")
        rc, out = ssh(f"ax apply -f /tmp/{name}.yaml")
    if rc != 0:
        return False, "apply failed: " + out
    # order verified by the sentinel-probe run: the actor (egress parent)
    # only comes up after a resume, so: resume → egress → resume
    ssh(f"ax resume {name}")
    ok, out = apply_egress(name, hosts, cidrs)
    if not ok and "does not exist" in out:
        # actor creation is asynchronous right after apply — retry briefly
        for _ in range(6):
            time.sleep(15)
            ok, out = apply_egress(name, hosts, cidrs)
            if ok:
                break
    if not ok:
        return False, "egress failed: " + out
    rc, out = ssh(f"ax resume {name}")
    if rc != 0 and "already" not in out.lower():
        return False, "resume failed: " + out
    return True, out


def poll_result(name, timeout=POLL_TIMEOUT, not_before=None):
    if not_before is None:
        not_before = time.time() - 60
    deadline = time.time() + timeout
    cmd = RECEIVER_POLL_CMD.format(name=name)
    while time.time() < deadline:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=45)
        out = p.stdout.strip()
        if out:
            try:
                # tail -1 of potentially several runs; take the newest file content
                obj = json.loads(out.splitlines()[-1])
                if obj.get("task") == name and \
                        obj.get("ts", 0) > not_before:
                    return obj
            except ValueError:
                pass
        time.sleep(POLL_INTERVAL)
    return None


def load_state():
    path = os.path.join(HERE, "state", "state.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(os.path.join(HERE, "state"), exist_ok=True)
    with open(os.path.join(HERE, "state", "state.json"), "w") as f:
        json.dump(state, f, indent=1)


def fetch_result_via_ssh(name):
    """Fallback: read newest result file for `name` directly via ssh cat."""
    rc, out = ssh(f"ls -t ~/ax-test/data/{name}-*.json 2>/dev/null | head -1")
    if rc == 0 and out.strip():
        rc2, raw = ssh("cat " + out.strip())
        if rc2 == 0 and raw.strip():
            try:
                return json.loads(raw.strip().splitlines()[-1])
            except ValueError:
                return None
    return None


def run():
    state = load_state()
    started = time.time()
    outcomes = []
    repo_dir = config.REPO_DIR
    tasks = []
    try:
        tasks.append(build_axrepo_task(repo_dir))
    except Exception as e:
        outcomes.append(("sentinel-axrepo", None, f"build failed: {e}"))
    try:
        tasks.append(build_upstream_task(state))
    except Exception as run_e:
        outcomes.append(("sentinel-upstream", None, f"build failed: {run_e}"))

    for name, src in tasks:
        manifest = manifest_for(name, src)
        if name == "sentinel-axrepo":
            hosts = ["pypi.org", "files.pythonhosted.org"]
            cidrs = ["100.65.215.34/32"]
        else:
            hosts = ["api.github.com"]
            cidrs = ["100.65.215.34/32"]
        ok, out = dispatch(name, manifest, hosts, cidrs)
        if not ok:
            outcomes.append((name, None, out))
            continue
        dispatched_at = time.time()
        res = poll_result(name, not_before=dispatched_at - 120)
        if res is None:
            res = fetch_result_via_ssh(name)
        if res is None:
            outcomes.append((name, None, "no result (timeout or post failed)"))
            continue
        outcomes.append((name, res, None))
        # update state from results
        if name == "sentinel-upstream" and res.get("results"):
            r = res["results"]
            state["upstream"] = {
                "main_sha": r.get("main_sha") or
                            state.get("upstream", {}).get("main_sha"),
                "tags": merge_tags(state, r),
            }
            save_state(state)
        elif name == "sentinel-axrepo" and res.get("results"):
            state["axrepo"] = {"sha": res["results"].get("sha"),
                               "checked_at": started}
            save_state(state)

    return outcomes, started


def merge_tags(state, r):
    known = state.get("upstream", {}).get("tags", ["v0.3.1"])
    new = r.get("new_tags") or []
    return sorted(set(known + new))


def render_digest(outcomes, started):
    lines = ["AX Sentinel — daily repo report", ""]
    total_ok = 0
    for name, res, err in outcomes:
        if err:
            lines.append(f"▪ {name}: ERROR — {err}")
            continue
        total_ok += 1
        md = (res or {}).get("md", "")
        lines.append(f"▪ {name}: OK")
        for ln in md.splitlines():
            lines.append("  " + ln)
    lines.append("")
    lines.append(f"tasks ok: {total_ok}/{len(outcomes)} · "
                 f"wall {int(time.time() - started)}s · "
                 f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    return "\n".join(lines)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "run":
        outcomes, started = run()
        digest = render_digest(outcomes, started)
        os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
        with open(os.path.join(HERE, "out", "digest.txt"), "w") as f:
            digest and f.write(digest)
        print(digest)
    elif mode == "digest":
        outcomes, started = run()
        print(render_digest(outcomes, started))
    elif mode == "status":
        rc, out = ssh("ax get tasks")
        print(out or "(empty)")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
