"""Unit tests — stdlib unittest, no network. Run: python3 -m unittest discover"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import axcli  # noqa: E402
import kube  # noqa: E402
import state as state_mod  # noqa: E402
import telegram  # noqa: E402
import watcher  # noqa: E402


class TestState(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            st = state_mod.load(p)
            st["offset"] = 42
            state_mod.save(p, st)
            self.assertEqual(state_mod.load(p)["offset"], 42)

    def test_missing_and_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            self.assertEqual(state_mod.load(p), state_mod.DEFAULTS)
            with open(p, "w") as f:
                f.write("{corrupt")
            self.assertEqual(state_mod.load(p), state_mod.DEFAULTS)


class TestTelegramChunking(unittest.TestCase):
    def test_short(self):
        self.assertEqual(telegram.split_message("hi"), ["hi"])

    def test_long(self):
        chunks = telegram.split_message("\n".join(f"line{i}" for i in
                                                  range(1000)))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= telegram.MAX_LEN for c in chunks))
        self.assertEqual("\n".join(chunks).count("\nline"), 999)

    def test_huge_single_line(self):
        chunks = telegram.split_message("x" * 12000)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(len(c) <= telegram.MAX_LEN for c in chunks))


class TestAxcli(unittest.TestCase):
    def test_run_uses_login_shell(self):
        cap = {}
        fake = subprocess.CompletedProcess(args=[], returncode=0,
                                           stdout="tasks", stderr="")
        with mock.patch.object(subprocess, "run") as m:
            m.side_effect = \
                lambda a, **k: (cap.update(args=a) or fake)
            r = axcli.run(["get", "tasks"])
        self.assertEqual(cap["args"], ["bash", "-lc", "ax get tasks"])
        self.assertEqual(r.rc, 0)

    def test_usage_detector(self):
        self.assertFalse(axcli.looks_like_usage(
            "NAME   ATESPACE   PHASE\nfoo bar\n"),
            "successful task listing must NOT be flagged as usage")
        self.assertTrue(axcli.looks_like_usage("Usage: ax get ..."))
        self.assertTrue(axcli.looks_like_usage(
            "ax — manage tasks\n\nUsage: ax <command>"))


class TestUsageDetectorRaises(unittest.TestCase):
    def test_raises_enverror(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="Usage: ax [flags] [command]", stderr="")
        with mock.patch.object(subprocess, "run", return_value=fake):
            with self.assertRaises(axcli.EnvError):
                axcli.run(["get", "tasks"])


class TestKube(unittest.TestCase):
    def test_extract_messages(self):
        raw = '\n'.join([
            json.dumps({"message": "hello", "level": "info"}),
            "plain line",
            json.dumps({"log": "from-log-field"}),
        ])
        self.assertEqual(kube.extract_messages(raw),
                         ["hello", "plain line", "from-log-field"])

    def test_cap(self):
        lines = [f"l{i}" for i in range(100)]
        capped = kube.cap_output(lines)
        self.assertIn("omitted", capped)
        self.assertIn("l0", capped)
        self.assertIn("l99", capped)
        self.assertNotIn("l50", capped)


class TestWatchers(unittest.TestCase):
    def test_single_push_per_transition(self):
        sent = []
        bot = mock.Mock()
        bot.send_message.side_effect = lambda c, t: sent.append(t)

        phases = iter(["Suspended", "Suspended", "Running", "Running"])

        class FakeAxcli:
            def run(self, args):
                class R:
                    rc = 0
                    out = f"phase: {next(phases)}\n"
                return R()

        w = watcher.Watchers(bot, FakeAxcli(), {"watches": {}}, "/dev/null")
        w.poll = 0
        # manual single-step the loop body (same logic as _loop)
        meta = {"chat": 1, "phase": None}
        w.state["watches"]["t1"] = meta
        for _ in range(4):
            phase = w.get_phase("t1")
            if meta["phase"] is not None and phase != meta["phase"]:
                w._send(meta["chat"], "transition")
            meta["phase"] = phase
        self.assertEqual(sent, ["transition"])


class TestRoute(unittest.TestCase):
    def test_route(self):
        import axbot as axbot_mod
        self.assertEqual(axbot_mod.route("/task foo bar"),
                         ("task", "foo bar"))
        self.assertEqual(axbot_mod.route("/TASKS@my_bot"),
                         ("tasks", ""))
        self.assertEqual(axbot_mod.route("hello"), (None, None))


if __name__ == "__main__":
    unittest.main()
