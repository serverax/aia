# Sprint 1 — Infrastructure & Echo Agent

Weeks 1–2. Proves the full event-driven plumbing end-to-end with a
do-nothing Echo Agent, so Sprint 2's Orchestrator can plug into a known-good
substrate.

## Deliverables (status)

| Deliverable | Status | Where it lives |
|---|---|---|
| K3s cluster (3-node Hetzner) | Script ready, run manually | `provision-cluster-full.sh` |
| Postgres deployment | K8s + docker-compose | `infrastructure/k3s/postgres.yaml`, `infrastructure/docker-compose.dev.yml` |
| Redis deployment | K8s + docker-compose | `infrastructure/k3s/redis.yaml`, `infrastructure/docker-compose.dev.yml` |
| OpenTelemetry + Jaeger | Code + manifests | `libs/communication/telemetry.py`, `infrastructure/k3s/jaeger.yaml` |
| Echo Agent (PoC) | Code + Dockerfile + manifest | `services/echo_agent/` |
| Integration tests | docker-compose driven | `tests/integration/test_echo_agent.py` |

## File map

```
F:\aia\
├── libs/communication/
│   ├── protocol.py            # original create_message() (kept)
│   ├── message.py             # AgentMessage / TaskAssignment / TaskResult pydantic models
│   ├── telemetry.py           # init_telemetry() — OTLP/gRPC → Jaeger
│   ├── redis_client.py        # Streams: ensure_group / consume / ack / publish
│   └── postgres_client.py     # build_pool() + audit()
├── services/echo_agent/       # underscore: hyphens are invalid in Python module names
│   ├── main.py                # FastAPI app + consumer loop
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── README.md
│   └── tests/test_main.py     # service-local unit tests
├── infrastructure/
│   ├── docker-compose.dev.yml # postgres + redis + jaeger + echo-agent
│   └── k3s/
│       ├── namespace.yaml     # synthetic-enterprise + quota + NetPol
│       ├── postgres.yaml      # StatefulSet + init ConfigMap + Secret
│       ├── postgres-init.sql  # audit_log schema (used by compose + k3s)
│       ├── redis.yaml         # StatefulSet
│       ├── jaeger.yaml        # all-in-one Deployment
│       └── echo-agent.yaml    # Deployment + Service + ConfigMap
└── tests/
    ├── conftest.py            # skip integration tests if dev stack down
    ├── unit/                  # test_protocol, test_message, test_telemetry
    └── integration/test_echo_agent.py
```

## Run locally

```bash
# 1. Bring up the dev stack
docker compose -f infrastructure/docker-compose.dev.yml up -d

# 2. Install deps
pip install -r requirements-dev.txt

# 3. Run all unit tests (no docker required)
pytest tests/unit services/echo_agent/tests -m unit

# 4. Run the integration test (requires docker stack up + agent reachable)
pytest tests/integration -m integration
```

Send a manual echo:

```bash
docker compose -f infrastructure/docker-compose.dev.yml exec redis \
  redis-cli XADD agent:echo:tasks '*' \
    from_agent dev-cli to_agent echo-agent-v1 task_id t1 \
    message_type echo status pending data '{}' metadata '{}'

docker compose -f infrastructure/docker-compose.dev.yml exec redis \
  redis-cli XREAD COUNT 1 STREAMS agent:echo:results 0
```

Jaeger UI: <http://localhost:16686>

## Deploy to Hetzner (after `provision-cluster-full.sh` runs)

```bash
export KUBECONFIG=~/.kube/aia-config.yaml

# 1. Namespace + NetworkPolicies + RBAC
kubectl apply -f infrastructure/k3s/namespace.yaml

# 2. Set the Postgres password before applying
#    (replace REPLACE_ME_BEFORE_APPLY in postgres.yaml or apply your own Secret)
kubectl apply -f infrastructure/k3s/postgres.yaml
kubectl apply -f infrastructure/k3s/redis.yaml
kubectl apply -f infrastructure/k3s/jaeger.yaml

# 3. Build + push the agent image, update the image: line, then apply
docker build -t ghcr.io/serverax/aia/echo-agent:latest -f services/echo_agent/Dockerfile .
docker push ghcr.io/serverax/aia/echo-agent:latest
kubectl apply -f infrastructure/k3s/echo-agent.yaml

# 4. Watch the rollout
kubectl rollout status -n synthetic-enterprise deployment/echo-agent
kubectl logs -n synthetic-enterprise -l app=echo-agent --tail=50
```

## Acceptance checklist

- [x] `libs/communication` exports `AgentMessage`, `create_message`,
      `init_telemetry`, Redis/Postgres helpers
- [x] Echo Agent boots against docker-compose dev stack
- [x] Sending an `AgentMessage` on `agent:echo:tasks` yields a matching
      echo on `agent:echo:results` within 30s
- [x] Each echo produces two `audit_log` rows (one `in`, one `out`)
- [x] Each echo produces a span visible in Jaeger UI
- [x] Unit tests run with no external services
- [x] Integration test skips cleanly when dev stack is down
- [ ] **K3s cluster provisioned on Hetzner** (blocked: requires you to run
      `provision-cluster-full.sh` from your WSL — see top of `provision-cluster-full.sh`)
- [ ] **Manifests applied to live cluster** (blocked on the above)

## Known gaps / TODO before Sprint 2 starts

- Postgres Secret in `postgres.yaml` has placeholder `REPLACE_ME_BEFORE_APPLY`
  — swap for the value saved in `~/.aia/secrets` by `provision-cluster-full.sh`,
  or use SealedSecrets.
- Echo Agent image reference in `echo-agent.yaml` points at GHCR but no CI
  push pipeline exists yet — this is the first thing Sprint 2 should add.
- Determinism / load tests are deferred to Sprint 8 hardening.
