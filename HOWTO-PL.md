# AX na serv2uk — instrukcja użycia (26/09/2026)

## Co masz
Stack: ax-server (systemd, 127.0.0.1:8494) + Redis (taski) + ax-controller (systemd) + ATE w k3s.
CLI: ~/go/bin/ax (AX_SERVER w ~/.profile → działa przez bash -lc). KUBECONFIG ~/.kube/config.
Registry: localhost:5001 (hostPort). Worker-pool w ns ax-system (2 pody, gVisor).

## Szybki start (30 sekund)
    ssh ubuntu@100.65.215.34
    sudo -iu hermes          # login shell → AX_SERVER i PATH ładują się same
    bash -lc "ax apply -f ~/ax-test/demo1.yaml && ax resume task demo1 && ax watch task demo1"

Task przechodzi Suspended → Running w ~15–20 s (workerIP 10.42.0.27).

## Jak to działa (mental model)
Task AX = dowolny kontener w klastrze, ale: tworzony przez API (nie kubectl),
stan w Redis (nie w etcd), suspend/resume z checkpointem, worker-pool z gVisorem.
Taski NIE są zasobem k8s — `kubectl get tasks` słusznie zwraca błąd.

## Codzienne komendy
    ax get tasks                  # lista tasków
    ax get task demo1             # szczegóły + faza + workerIP
    ax apply -f task.yaml         # utwórz (zawsze w fazie Suspended)
    ax resume task demo1          # uruchom
    ax suspend task demo1         # usypia (checkpoint do rustfs)
    ax watch task demo1           # live przejścia faz
    ax ssh demo1 -- hostname      # wejście do tasku (wymaga spec.debug:true + Running)
    ax delete task demo1          # usuń (dwufazowy: Terminating → gone)

## Cykl życia
Suspended → (resume) → Running → (suspend) → Suspended → (resume) → Running …
Task jest immutable: zmiana spec = delete + apply na nowo.

## Minimalny plik taska
    apiVersion: ax.io/v1alpha1
    kind: Task
    metadata:
      name: demo1
      atespace: default
    spec:
      image: localhost:5001/ax-task-runner@sha256:594e20cb...
      # debug: true   # dodaj, jeśli chcesz ax ssh

## Sprzątanie
    ax delete task demo1
    kubectl get pods -n ax-system    # worker-pool zostaje (stały)
Ręczne (awaryjne): redis-cli DEL ax:task:default:<name>; ZREM ax:tasks:atespace:default <name>

## Ograniczenia (zweryfikowane 26/09)
- ax ssh timeoutuje: alpha-build agentgateway nie wystawia portu, w który celuje CLI.
  Obejście: brak (pod-pool ateom jest distroless). Ograniczenie wersji, nie konfiguracji.
- Inne obrazy niż ax-task-runner (np. alpine): gVisor runsc exit 128 → Failed.
- CLI w nie-login ssh wypisuje help → zawsze bash -lc.

## Troubleshooting: Failed po suspend-resume
Objaw: resume konczy sie ActorResumeFailed / "Golden data resume requires the ActorTemplate golden tag".
Przyczyna: golden snapshot templateu nie zbudowal sie (np. bucket rustfs nie istnial w chwili create).
Diagnoza: ~/go/bin/kubectl-ate get actor-templates --all-atespaces   # kolumna ERROR
Naprawa: ax delete task X; kubectl-ate delete actor-template --atespace default <tmpl>;
         potem apply od nowa - fresh template zbuduje golden poprawnie.
Uwaga: swiezy task po apply potrafi przegrac wyscig z resume - drugi "ax resume task X" domyka.

## Agent pobierający dane z internetu (EGRESS — działa od 26/09 23:36)

### Warstwy, które muszą się zgrać (wszystkie wymagane!)
1. **Task** — zwykły YAML, komenda w `spec.command` (runner = Python 3.12).
2. **Egress-policy** — BEZ niej gateway odrzuca każdy CONNECT (fail-closed):
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
   Kolejność: ax apply (task wisi w Suspended) → create egress-policy → ax resume.
3. **Gateway** — musi być obraz ≥ v0.0.0-alpha.9e78d1da (fix agentgateway#3677;
   starsze odrzucały: "actor certificate has no ActorIdentity" 403).
   Sprawdź: kubectl get deploy -n ate-system atenet-egress -o jsonpath="{.spec.template.spec.containers[0].image}"

### Zapis danych
- `/workspace` = durable (przetrwa suspend/resume przez snapshot), ale NIE ma
  bezpośredniego dostępu z hosta (ax ssh w tej alphie nie działa).
- **Wzorzec praktyczny: POST na host.** Odbiornik na serv2:
       ~/ax-test/listener.log, port 18080 → zapisuje do ~/ax-test/data/out.json
  (nohup python3, start ręczny po reboocie — patrz ~/.bash_history 26/09).
  W polityce musi być cidr hosta (100.65.215.34/32).

### Gotowy przykład
`~/ax-test/fetch7.yaml` (pobiera repo info z api.github.com → POST na :18080).
Weryfikacja: cat ~/ax-test/data/out.json + tail ~/ax-test/listener.log.

### Debug
- Logi komendy taska: kubectl logs -n ax-system <ax-pod> | jq → labels.ate.actor.name
- Błędy tunelu: grep "atunnel" w logach ax-pool (403 = polityka/identity)
