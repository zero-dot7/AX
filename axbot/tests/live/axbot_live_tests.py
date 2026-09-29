#!/usr/bin/env python3
"""AX Bot LIVE e2e suite — each task goes through the REAL bot paths:
/gen (py attachment) -> manifest doc -> /apply (yaml attachment) -> task runs
-> live watcher delivers result to Telegram -> auto-delete. Driver restarts
the bot right after apply (race-guard lesson, skill: ax-substrate-ops)."""
import sys, os, time, json, subprocess, urllib.request

sys.path.insert(0, "/home/hermes/axbot/src")
import axbot as B  # noqa: E402

# The driver must NOT run in-process watcher threads: in earlier runs the
# driver's own watch thread won the race, FakeBot-swallowed the result and
# removed the watch before the live bot could rebuild it. Keep only the
# state write so the restarted live bot arms the real watcher.
def _watch_state_only(self, task, chat):
    with self._lock:
        self.state["watches"][task] = {"chat": chat, "phase": None,
                                       "since": time.time()}
        self._save()
B.Watchers.watch = _watch_state_only

ADMIN = "5063993049"
PENDING = "/tmp/live-pending"


class FakeBot:
    def __init__(self):
        self.sent, self.files = [], {}

    def sendMessage(self, chat_id, text):
        self.sent.append(("msg", chat_id, text)); return {}

    def get_file(self, file_id):
        return None, self.files[file_id]

    def sendDocument(self, chat_id, document, caption=None):
        self.sent.append(("doc", chat_id, document, caption)); return {}

    def send_document(self, chat_id, filename, data, caption=""):
        self.sent.append(("doc", chat_id, filename, data, caption)); return {}


class Ctx:
    def __init__(self, bot, chat_id):
        self.bot, self.chat = bot, {"id": chat_id}
        self.cfg = {"allowed": [str(chat_id)]}
        # real Watchers (state-only watch) so /apply persists the watch for
        # the restarted live bot — without this, ctx.watchers raises
        # AttributeError and the watch is silently never armed
        st = json.load(open("/home/hermes/.axbot/state.json"))
        self.watchers = B.Watchers(bot, None, st,
                                   "/home/hermes/.axbot/state.json")

    def reply(self, text):
        self.bot.sendMessage(self.chat["id"], text)


def upd(uid, doc=None, caption=None, text=None):
    m = {"message_id": uid, "chat": {"id": ADMIN}, "date": 0, "from": {"id": ADMIN}}
    if text:
        m["text"] = text
    if doc:
        m["document"] = doc; m["caption"] = caption
    return {"update_id": uid, "message": m}


results = []


def check(name, ok, info=""):
    results.append(bool(ok))
    print(("  ok: " if ok else "  FAIL: ") + name + (("  " + str(info)[:200]) if not ok else ""))
    return bool(ok)


def run_one(tag, py_path, sleep_s=95):
    print("LIVE %s (%s)" % (tag, py_path))
    fb, ctx = FakeBot(), None
    # 1) /gen
    fb.files["f1"] = open(py_path, "rb").read()
    ctx = Ctx(fb, ADMIN)
    B.handle_update(upd(1, doc={"file_id": "f1", "file_name": "s.py"}, caption="/gen " + tag), ctx)
    docs = [s for s in fb.sent if s[0] == "doc"]
    if not check("gen manifest emitted", bool(docs), fb.sent[-3:]):
        return False
    manifest = docs[-1][3]
    if isinstance(manifest, bytes):
        manifest = manifest.decode()
    open("/tmp/%s.yaml" % tag, "w").write(manifest)
    check("manifest kind:Task", "kind: Task" in manifest)
    # 2) /apply with the bot STOPPED (live bot's offset-save overwrote watches
    #    in previous runs; stopping kills the race at the root)
    subprocess.run(["bash", "-c", "export XDG_RUNTIME_DIR=/run/user/1002; systemctl --user stop axbot"])
    time.sleep(2)
    fb2 = FakeBot(); ctx2 = Ctx(fb2, ADMIN)
    fb2.files["f2"] = manifest.encode()
    B.handle_update(upd(2, doc={"file_id": "f2", "file_name": "%s.yaml" % tag}, caption="/apply"), ctx2)
    applied = any("applied" in s[2] or "created" in s[2] or "Running" in s[2] or "resume" in s[2]
                  for s in fb2.sent if s[0] == "msg")
    check("apply accepted", applied, fb2.sent[-3:])
    # 3) start bot -> watcher arms from the just-saved state
    subprocess.run(["bash", "-c", "export XDG_RUNTIME_DIR=/run/user/1002; systemctl --user start axbot"])
    time.sleep(3)
    active = subprocess.run(["bash", "-c", "export XDG_RUNTIME_DIR=/run/user/1002; systemctl --user is-active axbot"],
                            capture_output=True, text=True).stdout.strip()
    check("bot active after start", active == "active", active)
    return True


def reapply(tag):
    """Retry on egress race (policy-before-actor 403): delete -> wait -> re-apply."""
    manifest = open("/tmp/%s.yaml" % tag).read()
    subprocess.run(["bash", "-lc", "ax delete task %s" % tag], capture_output=True)
    time.sleep(14)
    subprocess.run(["bash", "-c", "export XDG_RUNTIME_DIR=/run/user/1002; systemctl --user stop axbot"])
    time.sleep(2)
    fb = FakeBot(); ctx = Ctx(fb, ADMIN)
    fb.files["f3"] = manifest.encode()
    B.handle_update(upd(3, doc={"file_id": "f3", "file_name": "%s.yaml" % tag}, caption="/apply"), ctx)
    subprocess.run(["bash", "-c", "export XDG_RUNTIME_DIR=/run/user/1002; systemctl --user start axbot"])
    print("    re-applied %s (egress race retry)" % tag)


def verify(tag, wait=95):
    print("VERIFY %s" % tag)
    time.sleep(wait)
    import glob
    hits = glob.glob(os.path.expanduser("~/ax-test/data/%s-*.json" % tag))
    if not hits:
        reapply(tag)
        time.sleep(wait)
        hits = glob.glob(os.path.expanduser("~/ax-test/data/%s-*.json" % tag))
    check("result file in data/", bool(hits), "no %s-* file" % tag)
    if hits:
        d = json.load(open(hits[-1]))
        check("result has md", bool(isinstance(d.get("md"), str) and d["md"]), d)
        print("    md: %s" % d["md"][:120])
    state = json.load(open("/home/hermes/.axbot/state.json"))
    check("watch removed (auto-delete done)", tag not in state.get("watches", {}), state.get("watches"))
    tasks = subprocess.run(["bash", "-lc", "ax get tasks 2>/dev/null"], capture_output=True, text=True).stdout
    check("task auto-deleted", tag not in tasks, tasks[:200])
    journal = subprocess.run(["bash", "-c",
                              "export XDG_RUNTIME_DIR=/run/user/1002; journalctl --user -u axbot --since '-4 min' --no-pager"],
                             capture_output=True, text=True).stdout
    check("journal: result sent to chat", ("result" in journal and "5063993049" in journal) or "sent" in journal,
          journal[-300:])


if __name__ == "__main__":
    seq = [("live-api", "/tmp/t-api.py"), ("live-calc", "/tmp/t-calc.py"), ("live-multi", "/tmp/t-multi.py")]
    for tag, path in seq:
        if run_one(tag, path):
            verify(tag)
    npass = sum(results); ntot = len(results)
    print("\n==== LIVE SUITE: %d pass / %d fail ====" % (npass, ntot - npass))
    sys.exit(0 if ntot - npass == 0 else 1)
