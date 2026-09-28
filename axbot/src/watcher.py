"""Phase-change watchers — one thread per watched task. B9, B10."""
import glob
import json
import os
import threading
import time

DATA_DIR = os.path.expanduser("~/ax-test/data")


def latest_result(task):
    """Newest receiver result file for a task, or None.

    Files are named <task>-<YYYYMMDD>-<HHMMSS>.json
    """
    try:
        files = sorted(glob.glob(os.path.join(
            DATA_DIR, f"{task}-*.json")), key=os.path.getmtime)
        return files[-1] if files else None
    except OSError:
        return None


class Watchers:
    def __init__(self, bot, axcli, state, state_path, poll=10):
        self.bot, self.axcli, self.state, self.state_path = \
            bot, axcli, state, state_path
        self.poll = poll
        self._lock = threading.Lock()
        self._threads = {}  # task -> Thread

    def get_phase(self, task):
        r = self.axcli.run(["get", "task", task])
        if r.rc != 0:
            return None
        for ln in r.out.split("\n"):
            ln = ln.strip()
            if ln.lower().startswith("phase:"):
                return ln.split(":", 1)[1].strip()
            if ln.lower().startswith("phase "):
                return ln.split(None, 1)[1].strip().split()[0]
        return None

    def watch(self, task, chat):
        with self._lock:
            self.state["watches"][task] = {"chat": chat, "phase": None,
                                           "since": time.time()}
            self._save()
            if task not in self._threads or \
                    not self._threads[task].is_alive():
                t = threading.Thread(target=self._loop, args=(task,),
                                     daemon=True, name=f"watch-{task}")
                self._threads[task] = t
                t.start()

    def unwatch(self, task):
        with self._lock:
            self.state["watches"].pop(task, None)
            self._save()

    def _save(self):
        try:
            import state as state_mod
            state_mod.save(self.state_path, self.state)
        except Exception:
            pass

    def _loop(self, task):
        while True:
            with self._lock:
                meta = self.state["watches"].get(task)
            if meta is None:
                return
            phase = self.get_phase(task)
            if phase is None:
                # task gone or ax error — stop watching after notice
                with self._lock:
                    self.state["watches"].pop(task, None)
                    self._save()
                self._send(meta["chat"], f"👁 {task}: task not found "
                                         f"(deleted?) — watch removed")
                return
            if meta["phase"] is not None and phase != meta["phase"]:
                self._send(meta["chat"], f"👁 {task}: {meta['phase']} → "
                                         f"{phase}")
                if phase.lower() in ("failed", "succeeded", "completed"):
                    if phase.lower() != "failed":
                        self._send_result(meta["chat"], task)
                    with self._lock:
                        self.state["watches"].pop(task, None)
                        self._save()
                    return
            # result-file trigger: a newer file in ~/ax-test/data means the
            # run finished even if the Task phase is stuck at Running
            path = latest_result(task)
            if path and path != meta.get("sent_file") and \
                    os.path.getmtime(path) > meta.get("since", 0):
                time.sleep(2)  # let the receiver finish writing
                path2 = latest_result(task)
                if path2 == path:
                    self._send_result(meta["chat"], task)
                    # auto-cleanup: one-shot tasks stay Running forever and
                    # the substrate controller re-resumes suspended ones, so
                    # delete the finished task to free the worker slot
                    print(f"watch: auto-deleting {task}...", flush=True)
                    try:
                        dr = self.axcli.run(["delete", "task", task])
                    except Exception as e:  # noqa: BLE001
                        print(f"watch: delete call raised: {e}", flush=True)
                        dr = None
                    ok = dr is not None and dr.rc == 0
                    print(f"watch: delete rc="
                          f"{getattr(dr, 'rc', '?')}", flush=True)
                    if ok:
                        self._send(meta["chat"],
                                   f"🗑 {task}: done — task deleted")
                    else:
                        self._send(meta["chat"],
                                   f"⚠️ {task}: delete failed — "
                                   f"{str(getattr(dr, 'out', 'raised'))[:200]}")
                    with self._lock:
                        self.state["watches"].pop(task, None)
                        self._save()
                    return
            with self._lock:
                if task in self.state["watches"]:
                    self.state["watches"][task]["phase"] = phase
                    self._save()
            time.sleep(self.poll)

    def _send(self, chat, text):
        try:
            self.bot.send_message(chat, text)
        except Exception:
            pass

    def _send_result(self, chat, task):
        """Send the newest receiver result as a Telegram document."""
        path = latest_result(task)
        if not path:
            self._send(chat, f"📄 {task}: no result file found in "
                             f"{DATA_DIR}")
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            caption = ""
            try:
                with open(path) as f:
                    caption = json.load(f).get("md", "")[:1000] or ""
            except Exception:
                pass
            self.bot.send_document(chat, os.path.basename(path), data,
                                   caption=f"📄 {task} result\n\n{caption}")
            print(f"result sent: {task} → chat {chat} "
                  f"({os.path.basename(path)})", flush=True)
        except Exception as e:
            self._send(chat, f"📄 {task}: result upload failed — {e}")

    def rebuild(self):
        for task in list(self.state["watches"]):
            self.watch(task, self.state["watches"][task]["chat"])
