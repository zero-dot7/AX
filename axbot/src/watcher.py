"""Phase-change watchers — one thread per watched task. B9, B10."""
import threading
import time


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
            self.state["watches"][task] = {"chat": chat, "phase": None}
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

    def rebuild(self):
        for task in list(self.state["watches"]):
            self.watch(task, self.state["watches"][task]["chat"])
