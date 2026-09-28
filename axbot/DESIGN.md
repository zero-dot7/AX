# axbot — Telegram control plane for AX

> Status: DESIGN (not yet implemented). See PLAN.md for the step-by-step build.

## Goal

Control the AX/ATE substrate on serv2uk from a private Telegram chat: submit
tasks, check states, fetch results/logs, get notified on phase changes —
without SSH-ing into the box.

## Why a standalone Python bot (and not the alternatives)

| Option | Verdict | Why |
|---|---|---|
| **Python long-polling bot on serv2 (chosen)** | ✅ | serv2 already has Python 3.12; Telegram API is reachable; no public ingress needed; ax CLI is local — no SSH hop, no extra API layer |
| Telegram **webhook** bot | ❌ | requires public TLS endpoint on serv2; the box has none and we don't want one |
| Extend the **Hermes gateway bot** | ❌ | couples ops tooling to the agent runtime; every command burns LLM tokens; Hermes restarts would take AX control down with it |
| Go / ax-native tool | ❌ | unnecessary; the ax CLI already IS the API; shelling out is the stable interface |

Dependency policy: **stdlib only** (`urllib`, `json`, `subprocess`, `threading`).
The command set is small; python-telegram-bot would add pip deps for no gain.
If the bot grows complex (inline keyboards, media), revisit.

## Architecture

```
iPhone (Telegram)
   ⇅
api.telegram.org            (outbound only — long polling, no inbound ports)
   ⇅
axbot  —  systemd service on serv2, user `hermes`
   ├── poller thread   : getUpdates loop (25 s timeout), offset persisted
   ├── axcli module    : subprocess wrapper → `bash -lc "ax …"` (login shell!)
   ├── kube module     : kubectl / kubectl-ate for logs + egress policies
   └── watcher threads : per-task phase polling → push on change
   └── state.json      : update offset, watch registry, egress policy memory
```

Single process, ~4 small modules, SQLite-free (state.json is enough at this
scale). Runs as a systemd **system** unit with `User=hermes` so the service
survives logout and gets a clean env (AX_SERVER set explicitly in the unit —
see bottleneck B1).

## Command surface

```
/help                      command list
/status                    stack health: ax-server ping, task count, watcher count
/tasks                     ax get tasks (table)
/task <name>               phase, conditions[].message (the REAL error), worker IP, age
/apply                     reply to this with a .yaml attachment → apply + pre-flight + resume
/resume <name>             resume, with double-resume race handling (B3)
/suspend <name>            suspend (checkpoint)
/delete <name>             two-step confirm (B8)
/logs <name> [lines]       kubectl logs ax-pool (ax ssh is unusable — B6)
/policy <actor>            show egress policy; auto re-applied on /apply (B4)
/watch <name>              push a message on every phase change
/unwatch <name>
/results <name>            download task artifacts (registered result paths)
```

## Security

- **Allowlist**: bot answers ONLY to configured Telegram user IDs; everyone
  else gets silence (not even "unauthorized" — no oracle for strangers).
- **Token**: separate bot (NOT the Hermes gateway bot), token in
  `/etc/axbot.env` (mode 600, `EnvironmentFile=`), never in the repo.
- **Delete/apply**: require explicit confirmation step.
- **Repo hygiene**: secret scan before every push must match `AIza…` AND
  `AQ.…` (existing repo rule).

## Bottlenecks and how the design absorbs them

- **B1 — ax CLI needs a login shell.** `AX_SERVER` lives in `~/.profile`,
  so a bare `subprocess` call prints help and exits 0 (looks like success!).
  Every invocation goes through `bash -lc "ax …"`, and the systemd unit sets
  `AX_SERVER` explicitly. The wrapper treats "printed usage/help" as failure.
- **B2 — Telegram 4096-char limit vs. huge ax output.** Output is capped
  (head+tail with a "… N lines omitted" marker) and chunked into ≤4000-char
  messages. `/task` shows a condensed view (phase + conditions only);
  full JSON goes to a file on request.
- **B3 — resume race after apply.** A resume issued immediately after apply
  can lose to task creation and leave the task Suspended. The bot polls
  until phase=Suspended, then resumes, then verifies Running and issues a
  second resume if still Suspended (verified procedure from ops notes).
- **B4 — deleting a task deletes its egress policy.** A re-applied task
  silently stays 403-blocked. The bot stores the policy manifest per task
  name (state.json) and re-creates it before resume automatically.
- **B5 — golden snapshot preconditions.** Resume without a built golden tag
  = FailedPrecondition. `/apply` pre-flight: snapshot bucket exists,
  template has a golden tag (via kubectl-ate). Warn BEFORE apply, since
  templates are immutable and a broken one needs delete+recreate.
- **B6 — `ax ssh` is broken (alpha gateway port-forward).** All interior
  access goes through `kubectl logs -n ax-system ax-pool-<pod>`; /logs
  extracts `message` fields from the JSON lines.
- **B7 — mutating-op races.** apply/resume/suspend/delete are serialized
  behind a single lock; read-only commands run freely.
- **B8 — destructive actions.** `/delete` requires a confirmation token
  echoed back by the user (state.json, 60 s TTL).
- **B9 — restart resilience.** Telegram update offset persisted after every
  batch → no double-processing after restart. Watchers rebuild from the
  registry on start; phase-change pushes dedupe on (task, phase).
- **B10 — notification spam.** Watcher polls at 10 s but only pushes on
  phase TRANSITIONS, max 1 message per transition; /status is pull-based.
- **B11 — secrets into tasks.** No native AX secrets; the bot never puts
  secret values into chat. Policy manifests with placeholders only;
  injection stays a server-side manual step.

## Deliberately out of scope (v1)

- Inline keyboards / rich UI — plain commands suffice on iPhone.
- Multi-tenant auth (roles) — single-admin allowlist.
- Editing task specs — tasks are immutable anyway; delete+apply is the
  workflow, and v1 keeps that manual via /apply with a fresh YAML.

## Deployment sketch

```
/etc/systemd/system/axbot.service
  [Service]
  User=hermes
  Environment=AX_SERVER=http://127.0.0.1:8494
  Environment=KUBECONFIG=/home/hermes/.kube/config
  EnvironmentFile=/etc/axbot.env        # TELEGRAM_TOKEN, ALLOWED_USER_IDS
  ExecStart=/usr/bin/python3 /home/hermes/axbot/axbot.py
  Restart=always
```

Code layout (repo folder `axbot/`):

```
axbot/
  DESIGN.md          this file
  PLAN.md            step-by-step implementation plan
  src/
    axbot.py         poller + command router (entrypoint)
    axcli.py         bash -lc wrapper: run(), output capping, usage-detector
    kube.py          kubectl / kubectl-ate helpers (logs, egress, golden)
    telegram.py      minimal Bot API client (getUpdates/sendMessage, stdlib)
    watcher.py       phase-change watcher threads
    state.py         state.json load/save (offset, watches, confirms, policies)
  tests/             unit tests with a fake subprocess / fake Bot API
  axbot.service      systemd unit (above)
  README.md          operator runbook (install, token setup, logs)
```
