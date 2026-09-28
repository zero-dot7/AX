"""ax CLI wrapper — every call via bash -lc, with usage-detector. B1."""
import shlex
import subprocess


class CmdResult:
    def __init__(self, rc, out, err):
        self.rc, self.out, self.err = rc, out, err

    def __str__(self):
        if self.err:
            return self.err.strip()
        return self.out.strip()


USAGE_MARKERS = ("Usage:", "usage:")


def looks_like_usage(out):
    """ax prints help and exits 0 when AX_SERVER is missing — detect it.

    NOTE: a successful `ax get tasks` also starts with 'NAME  ATESPACE',
    so only 'Usage:' lines count as the missing-env signal."""
    head = "\n".join(out.strip().split("\n")[:3])
    return any(m in head for m in USAGE_MARKERS)


def run(args, timeout=120, env_extra=None):
    """Run `ax <args>` in a login shell. Returns CmdResult; raises
    EnvError when the CLI printed usage (missing AX_SERVER)."""
    cmd = "ax " + " ".join(shlex.quote(a) for a in args)
    try:
        p = subprocess.run(["bash", "-lc", cmd], capture_output=True,
                           text=True, timeout=timeout, env=env_extra)
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"ax {args[0]}: timeout after {timeout}s") from None
    if p.returncode == 0 and looks_like_usage(p.stdout):
        raise EnvError(f"ax printed usage — AX_SERVER not set? cmd: {cmd}")
    return CmdResult(p.returncode, p.stdout, p.stderr)


class EnvError(Exception):
    pass
