# ax-sentinel

Cross-server repo sentinel: **serv** (the Hermes host, 100.118.55.1) dispatches
AX tasks over Tailscale to the AX substrate on **serv2uk** (100.65.215.34),
collects results from the receiver, and renders a daily text digest.

Two tasks per run:

| task | what it does | egress |
|---|---|---|
| `sentinel-axrepo` | downloads a `git archive HEAD` tarball of this repo (served over Tailscale HTTP :18081 on serv2uk), installs pyyaml, runs the offline test suite, scans for secrets (AIza/AQ./TG/GH tokens, redacted) | PyPI + serv2uk |
| `sentinel-upstream` | `git ls-remote` google/ax + GitHub compare API vs last known state → new commits/tags | api.github.com + serv2uk |

## Layout

```
ax-sentinel/
├── sentinel.py        # dispatcher — runs on serv
├── config.py          # config.yaml loader (stdlib only)
├── config.yaml        # repo_dir + watched repos
├── tasks/
│   ├── axrepo_task.py     # runs inside the AX runner ({{REPO_URL}}… substituted)
│   └── upstream_task.py   # runs inside the AX runner ({{KNOWN_SHA}}… substituted)
├── tests/
│   └── sentinel_offline_tests.py
├── state/state.json   # last known upstream sha/tags (updated per run)
└── out/               # manifests, repo tarball, digest.txt (gitignored)
```

## Usage (on serv, from the repo root)

```bash
python3 ax-sentinel/sentinel.py run      # dispatch + wait + digest to stdout
python3 ax-sentinel/sentinel.py digest   # same, re-render after run
python3 ax-sentinel/sentinel.py status   # ax get tasks via ssh
```

## Dispatch sequence (per task)

`scp manifest → ax apply → ax resume → kubectl-ate egress (retry ×6 if actor
not yet created) → ax resume → poll receiver :18080 (30 min cap) → fallback
ssh cat`

Order matters and was verified live: the actor (egress-policy parent) only
exists after the first resume; egress before the first resume fails with
`parent Actor does not exist`, and a re-apply (delete + apply) wipes the
egress policy — re-apply it after any delete+apply cycle.

## Pitfalls found (see TESTING.md for the full log)

- **Manifest size**: embedding the repo tarball as base64 in the task command
  produced a 220 KB manifest → actor creation failed with
  `actor template not found`. Fix: serve the tarball over Tailscale HTTP.
- **`yaml.safe_dump(obj, stream)` + positional default**: wrote 0-byte files.
  Use `f.write(yaml.safe_dump(...))`.
- **pip in the sandbox** takes ~15 min (throttled egress); poll timeout must
  be ≥ 30 min.
- **Task result regex**: the offline suite prints `N pass / M fail`, not
  `N/M`.
- **stale results**: receiver files persist across runs — poll with
  `ts > dispatch_time`.
- **nohup over ssh dies** when the session closes; use `setsid nohup … &
` for the tarball HTTP server.

## Security

- No GitHub tokens in the runner: the private repo ships as a `git archive`
  tarball over Tailscale-only HTTP.
- Secret scan results are redacted (file:line + label, never the value).
- Egress is allow-list per actor: only PyPI/GitHub API + serv2uk Tailscale IP.
- The tarball HTTP server (:18081) binds the Tailscale interface and serves
  nothing else.
