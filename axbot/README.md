# axbot — operator runbook

Telegram control plane for the AX/ATE substrate on serv2uk.
See `DESIGN.md` for architecture and `PLAN.md` for the build plan.

## Install

```bash
# on serv2, as hermes
mkdir -p ~/axbot && cd ~/axbot        # contents from this repo folder
sudo cp axbot.service /etc/systemd/system/
sudo tee /etc/axbot.env >/dev/null    # mode 600!
TELEGRAM_TOKEN=<from @BotFather>       # a DEDICATED bot, not the Hermes one
ALLOWED_USER_IDS=<your telegram id>
EOF
sudo chmod 600 /etc/axbot.env
sudo systemctl daemon-reload && sudo systemctl enable --now axbot
```

## Commands

| Command | Effect |
|---|---|
| `/help` | command list |
| `/status` | stack health: ax-server reachable, task count, active watchers |
| `/tasks` | `ax get tasks` |
| `/task <name>` | phase + real error (conditions[].message) + worker IP |
| `/apply` | reply with a .yaml attachment → pre-flight, apply, resume, egress re-apply |
| `/resume <name>` / `/suspend <name>` | lifecycle (resume handles the double-resume race) |
| `/delete <name>` | requires confirmation token (60 s TTL) |
| `/logs <name> [lines]` | task logs via kubectl (ax ssh is unusable on this build) |
| `/policy <actor>` | egress policy state |
| `/watch <name>` / `/unwatch <name>` | push on every phase transition |
| `/results <name>` | registered task artifacts |

## Troubleshooting

- **"ax printed usage" error** — the CLI lost `AX_SERVER`; the systemd unit
  sets it explicitly, so this means someone changed the unit. Check
  `systemctl cat axbot`.
- **Task stuck Suspended after /apply, no worker events** — egress policy
  missing (delete removes it). `/apply` re-applies automatically when it
  knows the policy; otherwise re-create it manually (see repo HOWTO).
- **FailedPrecondition: Golden data resume** — template's golden snapshot
  never built; template must be deleted and re-applied (immutable).
  `/apply` pre-flight warns before this happens.
- **Logs empty** — the pool pod may have rotated; `/task <name>` shows the
  current worker IP, /logs re-resolves the pod each call.

## Logs

```bash
sudo journalctl -u axbot -f
```

## Secrets policy

No secrets in this repo, ever. Token and allowlist live in
`/etc/axbot.env` on serv2 (mode 600). Before every push: scan for
`AIza…` and `AQ.…` (repo-wide rule).
