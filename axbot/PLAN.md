# axbot — Implementation Plan

> **For Hermes:** Implement task-by-task; verify each with the exact
> commands given. Repo: `zero-dot7/AX`, folder `axbot/`. English-only docs.

**Goal:** A single-file-per-module Python Telegram bot (stdlib only) running
as a systemd service on serv2uk, controlling the AX substrate from a private
chat via the local `ax` CLI.

**Architecture:** Long-polling poller thread + command router; `ax` CLI
wrapped via `bash -lc`; per-task phase watchers; JSON state file. No DB, no
inbound ports, no pip dependencies.

---

## Phase 0 — scaffolding

### Task 0.1: repo scaffold
- Create `axbot/src/`, `axbot/tests/` with `__init__.py` in tests.
- Copy DESIGN.md layout: empty stubs `axbot.py`, `axcli.py`, `kube.py`,
  `telegram.py`, `watcher.py`, `state.py` (each a module docstring + pass).
- `axbot/axbot.service` exactly as in DESIGN.md.
- Commit: `scaffold axbot modules`.

### Task 0.2: secrets policy
- `axbot/.gitignore` — ignores nothing real (no secrets will ever live in
  the repo), but documents the rule: token stays in `/etc/axbot.env`.
- README section "Secrets" — same rule + the repo-wide scan rule
  (`AIza…`, `AQ.…` before every push).

## Phase 1 — core plumbing (local, testable without Telegram)

### Task 1.1: `state.py`
- `load(path) -> dict` / `save(path, state)` with defaults:
  `offset=0, watches={}, confirms={}, policies={}`.
- Atomic save (write tmp + os.replace).
- Test: roundtrip + defaults on missing file + corrupted file → defaults.

### Task 1.2: `telegram.py`
- `class Bot`: `__init__(token)`, `get_updates(offset, timeout=25)`,
  `send_message(chat_id, text)` (split >4000 chars into chunks),
  HTTP via `urllib.request`, errors → `BotError`.
- 429 Retry-After handling: sleep and retry once.
- Test: chunking logic unit-tested with a fake urlopen; no network in tests.

### Task 1.3: `axcli.py`
- `run(args: list[str], timeout=120) -> CmdResult(rc, out, err)`.
- Wraps `bash -lc "ax …"` with `shlex.quote`d args.
- **Usage-detector**: rc==0 but output starts with "Usage:"/"NAME   ATESPACE"
  style help → treat as `EnvError` (the #1 pitfall: looks like success).
- Test: fake subprocess asserting the command is `bash -lc "ax get tasks"`;
  usage-detector unit tests.

### Task 1.4: `kube.py`
- `task_logs(task, lines=50)` → `kubectl logs -n ax-system ax-pool-<pod>`
  (pod resolved from task status `workerIP`/actor), extract `message` fields.
- `egress_show(actor, atespace)`, `egress_apply(actor, atespace, yaml_path)`
  via `kubectl-ate`.
- `golden_tag_ok(template, atespace)` via `kubectl-ate get actor-templates`.
- Test: pure functions (JSON-line extraction, policy-manifest validation)
  unit-tested; subprocess calls mocked.

## Phase 2 — commands

### Task 2.1: command router skeleton (`axbot.py`)
- Parse `/cmd arg` from messages; unknown → brief help; empty chat allowlist
  check (silence for strangers).
- Command table mapping → handler functions `handle(update, ctx)`.
- Test: router table dispatch with synthetic updates.

### Task 2.2: read-only commands
- `/help`, `/status` (ax-server ping = `ax get tasks` rc, task count,
  watchers), `/tasks`, `/task <name>` (condensed: phase + conditions
  messages), `/logs`.
- Output capping: 30 lines head + tail + "… N omitted".
- Test: handlers against a fake axcli returning canned outputs.

### Task 2.3: watcher (`watcher.py`)
- `Watch(t)` registry: thread per watched task, poll `ax get task X` every
  10 s, on phase transition → `bot.send_message` to the source chat, dedupe
  on (task, phase); auto-stop on Failed/deleted.
- Rebuild from state on startup.
- Test: fake clock/axcli, assert single push per transition.

### Task 2.4: mutating commands + bottlenecks
- `/apply`: pre-flight (B5 golden check), save YAML to
  `~/.axbot/tasks/<name>.yaml`, apply → wait Suspended → resume (B3:
  verify, second resume if needed) → egress re-apply if known (B4) →
  confirm Running.
- `/resume`, `/suspend`, `/delete` (B8: confirmation token, 60 s TTL),
  `/policy`, `/watch`, `/unwatch`, `/results` (registered artifact paths
  from `~/.axbot/tasks/<name>.results`).
- All behind one global mutation lock (B7).
- Test: fake axcli state machine (Suspended→Running) driving /apply
  end-to-end in-process.

## Phase 3 — deployment on serv2

### Task 3.1: deploy dry-run (no Telegram yet)
- rsync `axbot/` → `hermes@serv2:~/axbot/`; `python3 -m unittest discover`
  on serv2 (confirms 3.12 compat).
- Run `python3 axbot.py --selftest`: executes axcli.run("get","tasks"),
  kube.task_logs dry, prints results — no Telegram token needed.

### Task 3.2: create the bot + token
- User creates a NEW bot via @BotFather (do NOT reuse the Hermes gateway
  bot). Token → `/etc/axbot.env` (mode 600):
  `TELEGRAM_TOKEN=…`, `ALLOWED_USER_IDS=<user telegram id>`.
- Get the user's Telegram ID from the Hermes gateway config or a one-off
  `/start` log line.

### Task 3.3: systemd service
- Install `axbot.service`, `daemon-reload`, `enable --now`.
- Verify: `systemctl status axbot`, journal shows "polling started",
  `/status` from the user's phone answers within 2 s.

### Task 3.4: end-to-end acceptance (on real AX)
- `/apply` with `manifests/agent-loop1.yaml` → task Running ≤60 s.
- `/watch` + `/suspend` → push "Suspended" ≤15 s.
- `/delete` flow with confirmation.
- `/tasks` matches `ax get tasks` over SSH.

## Phase 4 — docs + PR

### Task 4.1: README runbook
- Install, token setup, service logs, command reference, troubleshooting
  (usage-detector meaning, 403 egress, golden snapshot).

### Task 4.2: PR
- Branch `axbot`, secret scan (`AIza…`, `AQ.…`), push, open PR.
- User merges (standing rule: user merges their own PRs).
