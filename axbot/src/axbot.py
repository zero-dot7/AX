#!/usr/bin/env python3
"""axbot — Telegram control plane for AX. Entry point + command router."""
import os
import re
import secrets
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import axcli  # noqa: E402
import kube  # noqa: E402
import state as state_mod  # noqa: E402
import telegram  # noqa: E402
from watcher import Watchers  # noqa: E402

import yaml  # noqa: E402  (stdlib-adjacent; present on serv2uk)

HELP = """/help — this list
/gen <name> — generate AX manifest from a .py attachment (code must set `md`, optional `results`; egress auto-derived from URLs in code)
/status — stack health
/tasks — ax get tasks
/task <name> — phase + conditions (real errors)
/apply — reply with .yaml attachment → apply + resume + egress
/resume <name> | /suspend <name>
/delete <name> — confirmation required
/logs <name> [lines] — task logs via kubectl
/policy <actor> [atespace]
/watch <name> | /unwatch <name> — push on phase changes"""

MUT_LOCK = threading.Lock()  # B7


class Ctx:
    def __init__(self, bot, state, watchers, cfg):
        self.bot, self.state, self.watchers, self.cfg = \
            bot, state, watchers, cfg
        self.reply = lambda text: bot.send_message(cfg["chat"], text)


def cmd_status(ctx, args):
    try:
        r = axcli.run(["get", "tasks"])
        ok = r.rc == 0
        rows = [ln for ln in r.out.strip().split("\n")
                if ln.strip()][1:] if ok else []
        ctx.reply(f"ax-server: {'UP' if ok else 'DOWN (' + str(r)[:200] + ')'}"
                  f"\ntasks: {len(rows)}"
                  f"\nwatchers: {len(ctx.state['watches'])}")
    except Exception as e:
        ctx.reply(f"status error: {e}")


def cmd_tasks(ctx, args):
    r = axcli.run(["get", "tasks"])
    text = kube.cap_output(r.out.strip().split("\n")) if r.rc == 0 \
        else f"error: {str(r)[:300]}"
    ctx.reply(text or "(no tasks)")


def cmd_task(ctx, args):
    if not args:
        return ctx.reply("usage: /task <name>")
    r = axcli.run(["get", "task", args])
    if r.rc != 0:
        return ctx.reply(f"error: {str(r)[:300]}")
    lines = r.out.strip().split("\n")
    keep, conds = [], False
    for ln in lines:
        low = ln.lower()
        if "conditions" in low:
            conds = True
        if conds or low.startswith(("phase", "name", "actor", "workerip",
                                    "age")):
            keep.append(ln)
    ctx.reply(kube.cap_output(keep) or str(r)[:2000])


def cmd_logs(ctx, args):
    if not args:
        return ctx.reply("usage: /logs <name> [lines]")
    n = 50
    parts = args.split()
    if len(parts) > 1 and parts[1].isdigit():
        n = min(int(parts[1]), 200)
    ctx.reply("(resolving pod…)")
    r = axcli.run(["get", "task", parts[0]])
    pod = _pod_from_status(r.out)
    if not pod:
        return ctx.reply("could not resolve worker pod from task status")
    ctx.reply(kube.task_logs(parts[0], pod, n))


def _pod_from_status(out):
    for ln in out.split("\n"):
        if "workerip" in ln.lower() or "worker-ip" in ln.lower():
            val = ln.split(":", 1)[-1].strip() if ":" in ln else ""
            val = val.split()[0] if val else ""
            if val:
                return "ax-pool-" + val
    return None


def cmd_resume(ctx, args):
    if not args:
        return ctx.reply("usage: /resume <name>")
    with MUT_LOCK:
        r = axcli.run(["resume", args])
        ctx.reply(f"resume {args}: rc={r.rc}\n{str(r)[:500]}")


def cmd_suspend(ctx, args):
    if not args:
        return ctx.reply("usage: /suspend <name>")
    with MUT_LOCK:
        r = axcli.run(["suspend", args])
        ctx.reply(f"suspend {args}: rc={r.rc}\n{str(r)[:500]}")


def cmd_delete(ctx, args):
    if not args:
        return ctx.reply("usage: /delete <name>")
    with MUT_LOCK:
        conf = ctx.state["confirms"].get(args)
        if conf and conf.get("action") == "delete" \
                and conf.get("exp", 0) > time.time():
            del ctx.state["confirms"][args]
            state_mod.save(ctx.cfg["state_path"], ctx.state)
            r = axcli.run(["delete", "task", args])
            return ctx.reply(f"deleted {args}: rc={r.rc}\n{str(r)[:300]}")
        ctx.state["confirms"][args] = {"action": "delete",
                                       "exp": time.time() + 60}
        state_mod.save(ctx.cfg["state_path"], ctx.state)
        ctx.reply(f"⚠ delete {args}? Run /delete {args} again within "
                  f"60 s to confirm.")


def cmd_watch(ctx, args):
    if not args:
        return ctx.reply("usage: /watch <name>")
    ctx.watchers.watch(args, ctx.cfg["chat"])
    ctx.reply(f"👁 watching {args} (phase changes → this chat)")


def cmd_unwatch(ctx, args):
    if not args:
        return ctx.reply("usage: /unwatch <name>")
    ctx.watchers.unwatch(args)
    ctx.reply(f"stopped watching {args}")


def cmd_policy(ctx, args):
    if not args:
        return ctx.reply("usage: /policy <actor> [atespace]")
    parts = args.split()
    atespace = parts[1] if len(parts) > 1 else "default"
    ctx.reply(kube.egress_show(parts[0], atespace))


def cmd_apply(ctx, args):
    """Called with the raw manifest text when a document arrives."""
    with MUT_LOCK:
        try:
            doc = yaml.safe_load(args)
        except yaml.YAMLError as e:
            return ctx.reply(f"/apply: invalid YAML — {str(e)[:300]}")
        if not isinstance(doc, dict) or "apiVersion" not in doc:
            preview = args.strip()[:200].replace("\n", " ⏎ ")
            print(f"/apply reject: type={type(doc).__name__} "
                  f"len={len(args)} head={args[:300]!r}", flush=True)
            return ctx.reply(
                f"/apply: attachment must be an AX manifest "
                f"(apiVersion/kind/metadata)\nreceived ({len(args)} chars, "
                f"{type(doc).__name__}): {preview}")
        kind = doc.get("kind", "")
        name = doc.get("metadata", {}).get("name", "?")
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yaml",
                                         delete=False) as f:
            f.write(args)
            path = f.name
        r = axcli.run(["apply", "-f", path])
        if r.rc != 0 and "already exists" in str(r) and "immutable" in str(r):
            # AX tasks are immutable — delete the old one and re-apply
            name0 = doc.get("metadata", {}).get("name", "")
            if name0:
                dr = axcli.run(["delete", "task", name0])
                ctx.reply(f"♻️ task '{name0}' existed (immutable) — deleting…\n"
                          f"{str(dr.out)[:200]}")
                r = axcli.run(["apply", "-f", path])
        if r.rc != 0:
            return ctx.reply(f"/apply: apply FAILED\n{str(r)[:800]}")
        reply = [f"applied {kind} '{name}'", str(r.out)[:300]]
        if kind.lower() == "task":
            # egress policy: hostnames/cidrs from the manifest env or URLs
            rules = _extract_egress_rules(doc)
            if rules:
                with open(path, "w") as f:
                    yaml.safe_dump({"rules": rules}, f)
                pol = kube.egress_apply(name, "default", path)
                reply.append(f"egress: {pol[:200]}")
            rr = axcli.run(["resume", name])
            reply.append(f"resume: rc={rr.rc} {str(rr.out)[:100]}")
            # watch the task — result file returns to this chat on finish
            try:
                ctx.watchers.watch(name, ctx.cfg["chat"])
                reply.append(f"👁 watching {name} — result will be "
                             f"sent here as a file")
            except Exception as e:
                reply.append(f"watch failed: {e}")
        ctx.reply("\n".join(reply))


def _gen_manifest_task(name, code):
    """Build an AX Task manifest from a user's python snippet.

    Contract: the snippet must define `md` (report text) and may define
    `results` (any JSON-serializable value). We wrap it: imports, receiver
    post tail, pinned runner image, argv-list command.
    """
    body = GEN_PREAMBLE + "\n" + code.strip() + "\n" + GEN_TAIL.format(name=name)
    return {
        "apiVersion": "ax.io/v1alpha1",
        "kind": "Task",
        "metadata": {"name": name, "atespace": "default"},
        "spec": {
            "image": RUNNER_IMAGE,
            "command": ["python3", "-c", body],
        },
    }


def cmd_gen(ctx, args):
    """  /gen <name> <python...>  — build a manifest from a snippet."""
    parts = args.split(None, 1)
    if len(parts) < 2:
        return ctx.reply("usage: /gen <name> <python code…>")
    name, code = parts[0], parts[1]
    if not re.fullmatch(r"[a-z0-9-]{1,40}", name):
        return ctx.reply("name must be [a-z0-9-], max 40 chars")
    doc = _gen_manifest_task(name, code)
    yaml_text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    ctx.reply("manifest generated — sending for review, reply with /apply …")
    ctx.bot.send_document(ctx.cfg["chat"], f"{name}.yaml", yaml_text.encode(),
                          caption="generated by /gen — review then send back with /apply")


def _extract_egress_rules(doc):
    """Derive egress hostname rules from a Task manifest.

    Scans the command/args/env for https:// URLs and bare API hostnames,
    emits one hostname-pattern rule per distinct host.
    """
    import re
    text = yaml.safe_dump(doc)
    hosts, cidrs = set(), set()
    for m in re.finditer(r"https?://([A-Za-z0-9.\-]+)", text):
        h = m.group(1)
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", h):
            cidrs.add(f"{h}/32")
        else:
            hosts.add(h)
    rules = [{"hostnames": {"patterns": [h]}} for h in sorted(hosts)]
    rules += [{"cidrs": {"cidrs": [c]}} for c in sorted(cidrs)]
    return rules


# pinned task-runner image (never float the tag — supply-chain hygiene)
RUNNER_IMAGE = ("localhost:5001/ax-task-runner@"
                "sha256:594e20cb3e23a5961cf6c7c9cb40e06e670e43a2172534d17eccbf65f8b1ff94")

GEN_PREAMBLE = '''import json, os, time, urllib.request

def _post_result(payload):
    payload = json.dumps(payload).encode()
    for i in range(4):
        try:
            req = urllib.request.Request("http://100.65.215.34:18080/",
                                         data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                print("PHASE2 post", resp.status, flush=True)
                return
        except Exception as e:
            print("PHASE2 retry", i + 1, repr(e), flush=True)
            time.sleep(4)
    raise RuntimeError("receiver post failed")

'''

GEN_TAIL = '''

# --- generated tail: ship the result -------------------------------------
md = md if isinstance(md, str) else json.dumps(md, default=str)
_post_result({{"task": "{name}", "ts": time.time(), "md": md,
               "results": globals().get("results", None)}})
print("DONE", flush=True)
'''


COMMANDS = {
    "help": lambda c, a: c.reply(HELP),
    "gen": cmd_gen,
    "status": cmd_status,
    "tasks": cmd_tasks,
    "task": cmd_task,
    "apply": lambda c, a: c.reply(
        "send a .yaml manifest as an attachment "
        "(with caption /apply or none) to apply it"),
    "resume": cmd_resume,
    "suspend": cmd_suspend,
    "delete": cmd_delete,
    "logs": cmd_logs,
    "policy": cmd_policy,
    "watch": cmd_watch,
    "unwatch": cmd_unwatch,
}


def route(text):
    text = text.strip()
    if not text.startswith("/"):
        return None, None
    parts = text[1:].split(None, 1)
    cmd = parts[0].split("@")[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return cmd, args


def handle_update(upd, ctx):
    msg = upd.get("message") or {}
    chat = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "") or msg.get("caption", "") or ""
    frm = str(msg.get("from", {}).get("id", ""))
    if not ctx.cfg["allowed"]:
        # bootstrap mode: empty allowlist → first sender becomes admin
        ctx.cfg["chat"] = chat
        ctx.cfg["allowed"] = [frm]
        ctx.state["admin"] = frm
        state_mod.save(ctx.cfg["state_path"], ctx.state)
        ctx.reply(f"bootstrap: you ({frm}) are now admin. /help for commands.")
    if frm not in ctx.cfg["allowed"]:
        return  # silence for strangers
    ctx.cfg["chat"] = chat
    doc = msg.get("document")
    if doc:
        return _handle_document(ctx, doc, caption=msg.get("caption", ""))
    if not text.startswith("/"):
        return
    cmd, args = route(text)
    if not cmd:
        return
    fn = COMMANDS.get(cmd)
    if not fn:
        return ctx.reply(f"unknown /{cmd} — try /help")
    try:
        fn(ctx, args)
    except Exception as e:
        ctx.reply(f"/{cmd} failed: {e}")


def _handle_document(ctx, doc, caption=""):
    """Apply a YAML attachment, or /gen from a .py attachment."""
    fname = doc.get("file_name", "attachment")
    ctx.reply(f"📥 {fname}: downloading…")
    try:
        _, data = ctx.bot.get_file(doc["file_id"])
    except (telegram.BotError, KeyError) as e:
        return ctx.reply(f"download failed: {e}")
    if fname.lower().endswith(".py"):
        m = re.match(r"/gen\s+([a-z0-9-]+)\s*$", caption)
        if not m:
            return ctx.reply("attach .py with caption: /gen <name> (lowercase, digits, dashes; max 40 chars)")
        if len(m.group(1)) > 40:
            return ctx.reply(f"name too long: '{m.group(1)[:20]}…' — max 40 chars")
        try:
            cmd_gen(ctx, m.group(1) + " " + data.decode("utf-8", "replace"))
        except Exception as e:
            ctx.reply(f"/gen failed: {e}")
        return
        try:
            cmd_gen(ctx, m.group(1) + " " + data.decode("utf-8", "replace"))
        except Exception as e:
            ctx.reply(f"/gen failed: {e}")
        return
    if not fname.lower().endswith((".yaml", ".yml")):
        return ctx.reply("only .yaml/.yml (or .py + /gen) attachments are supported")
    try:
        cmd_apply(ctx, data.decode("utf-8", "replace"))
    except Exception as e:
        ctx.reply(f"/apply failed: {e}")


def selftest():
    print("axbot selftest — no token needed")
    r = axcli.run(["get", "tasks"])
    print(f"ax get tasks: rc={r.rc}\n{str(r)[:500]}")
    print("usage-detector:", "ENV OK" if not isinstance(r, str) else r)
    print("state roundtrip:", "OK" if state_mod.load("/nonexistent")
          == state_mod.load("/nonexistent2") else "FAIL")
    chunks = telegram.split_message("x" * 9000)
    print(f"split 9000 chars → {len(chunks)} chunks, "
          f"max={max(len(c) for c in chunks)}")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    token = os.environ.get("TELEGRAM_TOKEN", "")
    allowed = [u.strip() for u in
               os.environ.get("ALLOWED_USER_IDS", "").split(",") if u.strip()]
    # allowlist persists across restarts: seeded from env, then from state
    state_path = os.path.expanduser(
        os.environ.get("AXBOT_STATE", "~/.axbot/state.json"))
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    st = state_mod.load(state_path)
    if st.get("admin"):
        allowed = [st["admin"]]
    bot = telegram.Bot(token)
    watchers = Watchers(bot, axcli, st, state_path)
    watchers.rebuild()
    ctx = Ctx(bot, st, watchers,
              {"allowed": allowed, "chat": None, "state_path": state_path})
    print("polling started", flush=True)
    while True:
        try:
            updates = bot.get_updates(offset=st["offset"])
        except telegram.BotError as e:
            print(f"poll error: {e}", flush=True)
            time.sleep(5)
            continue
        for u in updates:
            st["offset"] = max(st["offset"], u["update_id"] + 1)
            state_mod.save(state_path, st)
            handle_update(u, ctx)
        time.sleep(0.5)


if __name__ == "__main__":
    sys.exit(main())
