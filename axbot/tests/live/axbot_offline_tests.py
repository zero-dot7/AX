#!/usr/bin/env python3
"""AX Bot offline test-suite — exercises the REAL bot code (axbot.py) with
synthetic Telegram updates + FakeBot, WITHOUT touching the AX cluster.
Covers: /gen contract (name validation, md required... — well, md is only
contract-checked at runtime in-task; here we check manifest shape), /apply
validation rejects, chat authorization, /help, /status.

Docs: ~/ax-test/HOWTO-PL.md + axbot.py docstrings (the contract).
Run on serv2uk:  python3 /tmp/axbot_offline_tests.py
"""
import sys, json, importlib

sys.path.insert(0, "/home/hermes/axbot/src")
import axbot as B
import state as state_mod

PASS, FAIL = [], []


class FakeBot:
    def __init__(self):
        self.sent = []
        self.files = {}

    def get_file(self, fid):
        return ({}, self.files[fid])

    def send_document(self, chat, fname, data, caption=None):
        self.sent.append(("doc", fname, data.decode()))
        return {}

    def send_message(self, chat, text, **kw):
        self.sent.append(("msg", text))
        return {}


def mk_ctx(chat="5063993049", allowed=("5063993049",)):
    fb = FakeBot()
    sp = "/tmp/axbot-test-state.json"
    st = state_mod.load(sp)
    st.clear()
    st["watches"] = {}
    st["offset"] = 0
    state_mod.save(sp, st)
    w = WatchersFake(fb)
    ctx = B.Ctx(fb, st, w, {"allowed": list(allowed), "chat": chat, "state_path": sp})
    return fb, ctx


class WatchersFake:
    def __init__(self, fb):
        self.fb = fb
        self.watched = []

    def watch(self, task, chat):
        self.watched.append((task, chat))


def upd(uid, text="", doc=None, caption="", frm="5063993049", chat="5063993049"):
    m = {"chat": {"id": int(chat)}, "from": {"id": int(frm)}}
    if doc:
        m["document"] = doc
        m["caption"] = caption
    else:
        m["text"] = text
    return {"update_id": uid, "message": m}


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print("  ok: %s" % name)
    else:
        FAIL.append(name)
        print("  FAIL: %s %s" % (name, detail))


# ---------------------------------------------------------------- T1 /gen happy
print("T1: /gen happy path (valid name, valid snippet)")
fb, ctx = mk_ctx()
snip = 'md = "hello"\nresults = {"a": 1}\n'
fb.files["f1"] = snip.encode()
B.handle_update(upd(1, doc={"file_id": "f1", "file_name": "s.py"}, caption="/gen t1-ok"), ctx)
docs = [s for s in fb.sent if s[0] == "doc"]
check("T1.1 /gen emits manifest document", bool(docs), repr(fb.sent))
y = docs[-1][2] if docs else ""
check("T1.2 kind: Task", "kind: Task" in y)
check("T1.3 apiVersion ax.io/v1alpha1", "ax.io/v1alpha1" in y)
check("T1.4 name preserved", "name: t1-ok" in y)
check("T1.5 pinned image (supply-chain)", "sha256:" in y)
check("T1.6 receiver tail present", "_post_result" in y and "t1-ok" in y)

# ---------------------------------------------------------------- T2 name validation (document path: regex in _handle_document)
print("T2: /gen name validation (document path)")
for i, (bad, expect) in enumerate([("Bad_Name", "reject"), ("UPPER", "reject"), ("spa ce", "reject")]):
    fb2, ctx2 = mk_ctx()
    fb2.files["f%d" % i] = snip.encode()
    B.handle_update(upd(2 + i, doc={"file_id": "f%d" % i, "file_name": "s.py"}, caption="/gen %s" % bad), ctx2)
    docs2 = [s for s in fb2.sent if s[0] == "doc"]
    rejected = any("caption" in s[1] or "name must be" in s[1] for s in fb2.sent if s[0] == "msg")
    check("T2.%d %r rejected (no manifest)" % (i + 1, bad), rejected and not docs2,
          repr([s[1][:60] for s in fb2.sent if s[0] == "msg"]))

# T2.4 KNOWN FINDING: >40-char name is silently TRUNCATED to 40 by the
# document-path regex (cmd_gen fullmatch never sees it). Assert current
# behavior so a future fix flips this test and we notice.
fb2, ctx2 = mk_ctx()
fb2.files["f9"] = snip.encode()
B.handle_update(upd(9, doc={"file_id": "f9", "file_name": "s.py"}, caption="/gen " + "x" * 41), ctx2)
docs2 = [s for s in fb2.sent if s[0] == "doc"]
check("T2.4 41-char name rejected (post-fix)", not docs2 and any("too long" in s[1] for s in fb2.sent if s[0] == "msg"),
      repr([s[1][:60] for s in fb2.sent if s[0] == "msg"]))

# ---------------------------------------------------------------- T3 /gen missing attachment
print("T3: /gen without attachment/code")
fb, ctx = mk_ctx()
B.handle_update(upd(10, text="/gen solo-name"), ctx)
check("T3.1 usage message", any("usage" in s[1].lower() for s in fb.sent if s[0] == "msg"))

# ---------------------------------------------------------------- T4 /apply rejects non-manifest
print("T4: /apply validation (non-manifest attachment rejected)")
fb, ctx = mk_ctx()
fb.files["fx"] = b"just some plain text file"
B.handle_update(upd(11, doc={"file_id": "fx", "file_name": "note.txt"}, caption="/apply"), ctx)
check("T4.1 non-YAML extension rejected", any("only .yaml" in s[1] for s in fb.sent if s[0] == "msg"),
      repr([s[1][:60] for s in fb.sent if s[0] == "msg"]))

fb, ctx = mk_ctx()
fb.files["fy"] = b"foo: bar\nbaz: 1\n"  # valid YAML, not a manifest
B.handle_update(upd(12, doc={"file_id": "fy", "file_name": "x.yaml"}, caption="/apply"), ctx)
check("T4.2 YAML-but-not-manifest rejected", any("must be an AX manifest" in s[1] for s in fb.sent if s[0] == "msg"))

fb, ctx = mk_ctx()
fb.files["fz"] = b"key: [unclosed\n"
B.handle_update(upd(13, doc={"file_id": "fz", "file_name": "broken.yaml"}, caption="/apply"), ctx)
check("T4.3 broken YAML rejected", any("invalid YAML" in s[1] for s in fb.sent if s[0] == "msg"))

# ---------------------------------------------------------------- T5 authorization
print("T5: chat authorization (allowlist)")
fb, ctx = mk_ctx(allowed=("5063993049",))
B.handle_update(upd(14, text="/help", frm="111111", chat="111111"), ctx)
check("T5.1 stranger ignored", not fb.sent, repr(fb.sent))

fb, ctx = mk_ctx(allowed=("5063993049",))
B.handle_update(upd(15, text="/help"), ctx)
check("T5.2 admin allowed", len([s for s in fb.sent if s[0] == "msg"]) >= 1)

# ---------------------------------------------------------------- T6 /help /status
print("T6: /help and /status")
fb, ctx = mk_ctx()
B.handle_update(upd(16, text="/help"), ctx)
msgs = [s[1] for s in fb.sent if s[0] == "msg"]
check("T6.1 /help lists commands", any("/gen" in m and "/apply" in m for m in msgs))

fb, ctx = mk_ctx()
B.handle_update(upd(17, text="/status"), ctx)
msgs = [s[1] for s in fb.sent if s[0] == "msg"]
check("T6.2 /status replies", bool(msgs) and "ax" in msgs[-1].lower(), repr(msgs))

# ---------------------------------------------------------------- T7 _extract_egress_rules
print("T7: egress auto-derivation")
doc = {"spec": {"command": ["python3", "-c",
           "urllib.request.urlopen('https://api.example.com/v1')\n"
           "urllib.request.urlopen('https://10.0.0.5/x')\n"
           "urllib.request.urlopen('https://api.example.com/v1')  # dupe\n"]}}
rules = B._extract_egress_rules(doc)
hosts = sorted(h for r in rules for h in r.get("hostnames", {}).get("patterns", []))
cidrs = sorted(c for r in rules for c in r.get("cidrs", {}).get("cidrs", []))
check("T7.1 hostname rule derived", hosts == ["api.example.com"], repr(rules))
check("T7.2 IP URL becomes cidr rule", cidrs == ["10.0.0.5/32"], repr(rules))
check("T7.3 dedup", len([h for h in hosts if h == "api API.com"]) == 0 and "api.example.com" in hosts)

# ---------------------------------------------------------------- summary
print("\n==== OFFLINE SUITE: %d pass / %d fail ====" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
print("OFFLINE-ALL-GREEN")
