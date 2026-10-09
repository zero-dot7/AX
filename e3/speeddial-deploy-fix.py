#!/usr/bin/env python3
"""speeddial-fix: jednorazowe zadanie analityczne — deploy przez E3 stack.

Wzorowane na night.py deploy(): scp template -> render server-side (klucz tylko
na serv2) -> apply -> egress (openrouter.ai + receiver) -> resume -> poll wyniku.
"""
import json, subprocess, sys, time

SERV2 = "hermes@100.65.215.34"
TASK = "speeddial-fix"
TPL = "/tmp/speeddial-fix.template.yaml"
RENDERED = "/tmp/speeddial-fix.rendered.yaml"
EGRESS = "/home/hermes/ax-test/speeddial-egress.json"
DATA_DIR = "/home/hermes/ax-test/data"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen/qwen3.8-flash"


def ssh(cmd, timeout=120):
    return subprocess.run(["ssh", SERV2, cmd], capture_output=True, text=True, timeout=timeout)


# 0) purge starych wyników + scp template
ssh(f"rm -f {DATA_DIR}/{TASK}-*.json")
subprocess.run(["scp", "-q", "/home/ubuntu/ax/manifests/speeddial-fix.template.yaml",
                f"{SERV2}:{TPL}"], check=True)

# 1) render server-side (klucz NIGDY nie opuszcza serv2)
INJECT = f"""python3 - <<'PYEOF'
key = [l.split('=',1)[1].strip().strip(chr(34)).strip(chr(39)) for l in open('/home/hermes/ax-test/openrouter-key.env') if 'OPENROUTER_API_KEY=' in l and not l.strip().startswith('#')][0]
assert len(key) == 73, f'key len {{len(key)}} != 73'
t = open('{TPL}').read()
assert '__GEMINI_KEY__' in t, 'placeholder missing'
open('{RENDERED}','w').write(
    t.replace('__GEMINI_KEY__', key)
     .replace('__MODEL_PROVIDER__', 'openai-compat')
     .replace('__LLM_MODEL__', '{MODEL}')
     .replace('__LLM_BASE_URL__', 'https://openrouter.ai/api/v1')
     .replace('__LLM_KEY__', key))
print('RENDER_OK')
PYEOF"""
p = ssh(f"chmod 600 {TPL} 2>/dev/null; {INJECT}")
print(p.stdout, p.stderr)
assert "RENDER_OK" in p.stdout, p.stderr

# 2) egress json (openrouter.ai + receiver IP)
egress_json = json.dumps({'rules': [
    {'hostnames': {'patterns': ['openrouter.ai']}},
    {'cidrs': {'cidrs': ['100.65.215.34/32']}},
]})
p = ssh(f'cat > {EGRESS} <<\'EOFJ\'\n{egress_json}\nEOFJ\ncat {EGRESS}')
assert "openrouter.ai" in p.stdout, p.stderr

# 3) apply + resume + egress-policy (retry, race z parent Actor)
DEPLOY = (
    "bash -lc 'ax delete task " + TASK + " 2>/dev/null; "
    "ax apply -f " + RENDERED + " && ax resume task " + TASK + "'"
)
p = ssh(DEPLOY, timeout=600)
print(p.stdout[-500:], p.stderr[-300:])

EG_RETRY = (
    "for i in $(seq 1 12); do sleep 10; "
    "if sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml "
    "/home/hermes/go/bin/kubectl-ate create egress-policy " + TASK +
    " -a default -f " + EGRESS + "; then EG=0; break; else EG=1; fi; "
    "done; [ \"$EG\" = \"0\" ] || exit 1"
)
p = ssh(EG_RETRY, timeout=300)
print("EGRESS:", p.returncode, p.stdout[-200:], p.stderr[-200:])
p = ssh(f"bash -lc 'ax resume task {TASK}'", timeout=300)
print("RESUME2:", p.returncode)
print("DEPLOY_DONE — polling wyniku (max 40 min)")
