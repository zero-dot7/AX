"""axbot state — JSON file, atomic saves. See DESIGN.md (B9)."""
import json
import os
import tempfile

DEFAULTS = {
    "offset": 0,
    "watches": {},   # task -> {"chat": id, "phase": last}
    "confirms": {},  # token -> {"action": ..., "task": ..., "exp": ts}
    "policies": {},  # task -> egress policy manifest path (B4)
}


def load(path):
    try:
        with open(path) as f:
            state = json.load(f)
    except (OSError, ValueError):
        return json.loads(json.dumps(DEFAULTS))
    for k, v in DEFAULTS.items():
        state.setdefault(k, json.loads(json.dumps(v)))
    return state


def save(path, state):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".axbot-state-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=1)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
