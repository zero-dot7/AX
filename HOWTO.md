# AX on serv2uk — operator guide (2026-09-26)

## What you have
Stack: ax-server (systemd, 127.0.0.1:8494) + Redis (tasks) + ax-controller (systemd) + ATE in k3s.
CLI: ~/go/bin/ax (AX_SERVER in ~/.profile → works via bash -lc). KUBECONFIG ~/.kube/config.
Registry: localhost:5001 (hostPort). Worker-pool in ns ax-system (2 pods, gVisor).

## Quick start (30 seconds)
    ssh ubuntu@100.65.215.34
    sudo -iu hermes          # login shell → AX_SERVER and PATH load themselves
    bash -lc "ax apply -f ~/ax-test/demo1.yaml && ax resume task demo1 && ax watch task demo1"

Task goes Suspended → Running in ~15–20 s (workerIP 10.42.0.27).

## Mental model
An AX task = any container in the cluster, but: created via API (not kubectl),
state in Redis (not etcd), suspend/resume with checkpoint, worker-pool with gVisor.
Tasks are NOT a k8s resource — `kubectl get tasks` rightly returns an error.

## Daily commands
    ax get tasks                  # list tasks
    ax get task demo1             # details + phase + workerIP
    ax apply -f task.yaml         # create (always in Suspended phase)
    ax resume task demo1          # start
    ax suspend task demo1         # sleep (checkpoint to rustfs)
    ax watch task demo1           # live phase transitions
    ax ssh demo1 -- hostname      # enter the task (requires spec.debug:true + Running)
    ax delete task demo1          # delete (two-phase: Terminating → gone)

## Lifecycle
Suspended → (resume) → Running → (suspend) → Suspended → (resume) → Running …
A task is immutable: changing spec = delete + apply anew.

## Minimal task file
    apiVersion: ax.io/v1alpha1
    kind: Task
    metadata:
      name: demo1
      atespace: default
    spec:
      image: localhost:5001/ax-task-runner@sha256:594e20cb...
      # debug: true   # add if you want ax ssh

## Cleanup
    ax delete task demo1
    kubectl get pods -n ax-system    # worker-pool stays (permanent)
Manual (emergency): redis-cli DEL ax:task:default:<name>; ZREM ax:tasks:atespace:default <name>

## Limitations (verified 2026-09-26)
- ax ssh times out: the alpha-build agentgateway does not expose the port the CLI targets.
  Workaround: none (the pod-pool ATEs are distroless). Version limitation, not config.
- Images other than ax-task-runner (e.g. alpine): gVisor runsc exit 128 → Failed.
- CLI over non-login ssh prints help → always use bash -lc.

## Troubleshooting: Failed after suspend-resume
Symptom: resume ends with ActorResumeFailed / "Golden data resume requires the ActorTemplate golden tag".
Cause: the golden snapshot template did not build (e.g. the rustfs bucket did not exist at create time).
Diagnose: ~/go/bin/kubectl-ate get actor-templates --all-atespaces   # ERROR column
Fix: ax delete task X; kubectl-ate delete actor-template --atespace default <tmpl>;
     then apply again — a fresh template builds the golden correctly.
Note: a fresh task after apply can lose the race with resume — a second "ax resume task X" closes it.

## Internet-fetching agent (EGRESS — working since 2026-09-26 23:36)

### Layers that must line up (all required!)
1. **Task** — plain YAML, command in `spec.command` (runner = Python 3.12).
2. **Egress-policy** — WITHOUT it the gateway rejects every CONNECT (fail-closed):
       cat > /tmp/eg.yaml <<Y
       metadata:
         name: default
       rules:
         - hostnames:
             patterns: ["api.github.com"]
         - cidrs:
             cidrs: ["100.65.215.34/32"]
       Y
       kubectl-ate create egress-policy <task> -a default -f /tmp/eg.yaml
   Order: ax apply (task hangs in Suspended) → create egress-policy → ax resume.
3. **Gateway** — must be image ≥ v0.0.0-alpha.9e78d1da (agentgateway#3677 fix;
   older ones reject with: "actor certificate has no ActorIdentity" 403).
   Check: kubectl get deploy -n ate-system atenet-egress -o jsonpath="{.spec.template.spec.containers[0].image}"

### Writing data out
- `/workspace` = durable (survives suspend/resume via snapshot), but there is NO
  direct access from the host (ax ssh does not work in this alpha).
- **Practical pattern: POST to the host.** Receiver on serv2:
       ~/ax-test/listener.log, port 18080 → writes to ~/ax-test/data/out.json
  (nohup python3, started manually after reboot — see ~/.bash_history 2026-09-26).
  The policy must include the host cidr (100.65.215.34/32).

### Ready example
`~/ax-test/fetch7.yaml` (fetches repo info from api.github.com → POST to :18080).
Verify: cat ~/ax-test/data/out.json + tail ~/ax-test/listener.log.

### Debug
- Task command logs: kubectl logs -n ax-system <ax-pod> | jq → labels.ate.actor.name
- Tunnel errors: grep "atunnel" in ax-pool logs (403 = policy/identity)
