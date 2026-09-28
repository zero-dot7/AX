"""kubectl / kubectl-ate helpers. See DESIGN.md (B4, B5, B6)."""
import json
import shlex
import subprocess


def _run(cmd, timeout=60):
    try:
        p = subprocess.run(["bash", "-lc", " ".join(
            shlex.quote(c) for c in cmd)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return p.returncode, p.stdout, p.stderr


def extract_messages(raw_logs, lines=None):
    """Extract `message` fields from JSON log lines; keep non-JSON lines."""
    out = []
    for ln in raw_logs.strip().split("\n"):
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            msg = obj.get("message") or obj.get("log") or ln
        except ValueError:
            msg = ln
        out.append(msg)
    return out if lines is None else out[-lines:]


def cap_output(lines, head=30, tail=30):
    """Cap long output: head+tail with an omission marker. B2."""
    if len(lines) <= head + tail + 2:
        return "\n".join(lines)
    omitted = len(lines) - head - tail
    return "\n".join(lines[:head] + [f"… {omitted} lines omitted …"]
                     + lines[-tail:])


def task_logs(task, pod, lines=50):
    rc, out, err = _run(["kubectl", "logs", "-n", "ax-system", pod,
                         f"--tail={lines * 4}"])
    if rc != 0:
        return f"logs error: {err.strip() or out.strip()}"
    msgs = extract_messages(out)
    sel = [m for m in msgs if task in m]
    if not sel:
        sel = msgs
    return cap_output(sel, head=lines, tail=0) or "(empty)"


def egress_show(actor, atespace):
    rc, out, err = _run(["kubectl-ate", "get", "egress-policy", actor,
                         "-a", atespace, "-o", "json"])
    if rc != 0:
        return f"policy error: {err.strip() or out.strip()}" \
            or f"(no egress policy for actor '{actor}')"
    return out.strip() or "(empty)"


def egress_apply(actor, atespace, yaml_path):
    # create fails if a policy already exists → delete first for idempotency
    _run(["kubectl-ate", "delete", "egress-policy", actor, "-a", atespace])
    rc, out, err = _run(["kubectl-ate", "create", "egress-policy", actor,
                         "-a", atespace, "-f", yaml_path])
    if rc != 0:
        return f"egress apply FAILED: {err.strip() or out.strip()}"
    return out.strip() or "applied"


def golden_tag_ok(template, atespace):
    """True if the actor template has a golden snapshot tag. B5."""
    rc, out, err = _run(["kubectl-ate", "get", "actortemplates", "-n",
                         atespace, "-o", "json"])
    if rc != 0:
        return None  # unknown — do not block apply
    try:
        items = json.loads(out).get("items", [])
    except ValueError:
        return None
    for it in items:
        if it.get("metadata", {}).get("name") == template:
            tags = it.get("spec", {}).get("goldenTags") \
                or it.get("status", {}).get("goldenTags") or []
            return bool(tags)
    return None  # template not found — let apply surface the error
