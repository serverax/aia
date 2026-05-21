# Sprint 6 — WASM Security Layer

Weeks 12–13. Sandboxes LLM-invoked tool execution in signed WASM
modules, hardens the cluster with admission policies, and enforces
per-agent capabilities.

**Design lock:** `claude-code/sprint-6/DESIGN.md` (approved decisions D1–D10).
**Preflight runbook:** `infrastructure/vault/PREFLIGHT-UNSEAL.md`.
**Tool roadmap:** `docs/WASM-TOOLS-ROADMAP.md`.

## Deliverables (status)

| Deliverable | Status | Where |
|---|---|---|
| WASM executor (wasmtime-py, fuel + memory + WASI denial) | Done | `services/tool_sandbox/executor.py` |
| Cosign signature verifier (pure Python, ECDSA-P256) | Done | `services/tool_sandbox/verifier.py` |
| Signed tool registry (ACL + schema validate + audit) | Done | `services/tool_sandbox/registry.py` |
| Rust SDK + first reference tool (`parse_dates_v3`) | Done | `tools/sdk/`, `tools/parse_dates_v3/` |
| Build + sign script (3 modes: prod / test / skip) | Done | `scripts/security/build-and-sign-tools.sh` |
| Claude tool-use protocol (`agent_loop`) | Done | `libs/llm/tools.py` |
| Anthropic SDK integration | Done | `libs/llm/client.py::AnthropicClient.chat_with_tools` |
| Orchestrator ToolRegistry wiring | Done | `services/orchestrator_agent/main.py` |
| Analyst Agent skeleton with `agent_loop` | Done | `services/analyst_agent/main.py` |
| Postgres audit adapter (SHA-256 digest of input/output) | Done | `services/tool_sandbox/audit_adapter.py` |
| audit_log migration (direction='tool') | Done | `infrastructure/k3s/migrations/0002_audit_tool.sql` |
| ARC custom runner image (Rust + cosign + vault CLI) | Drafted | `infrastructure/security/runner-image/Dockerfile` |
| sigstore/policy-controller ClusterImagePolicy | Drafted | `infrastructure/security/cluster-image-policy.yaml` |
| Kyverno pod-hardening ClusterPolicies (5 rules) | Drafted | `infrastructure/security/kyverno-policies.yaml` |
| Cluster install runbook | Done | `infrastructure/security/INSTALL.md` |
| Security E2E tests (sigstore, Kyverno, NetworkPolicy) | Scaffolded | `tests/security/` — skip without cluster |
| CI: build + sign all 4 agent images | Done | `.github/workflows/ci.yml` |

## File map (new in Sprint 6)

```
F:\aia\
├── libs/llm/tools.py                      # Claude tool-use protocol
├── libs/llm/client.py                     # + chat_with_tools()
├── services/tool_sandbox/                 # WASM executor + verifier + registry + audit adapter
│   ├── executor.py
│   ├── verifier.py
│   ├── registry.py
│   ├── audit_adapter.py
│   └── tests/                             # 24 unit tests
├── services/analyst_agent/main.py         # NEW — agent_loop + ToolRegistry
├── services/orchestrator_agent/main.py    # + conditional ToolRegistry
├── tools/                                 # NEW root
│   ├── Cargo.toml                         # workspace
│   ├── sdk/                               # shared Rust crate
│   └── parse_dates_v3/                    # first reference tool
├── infrastructure/
│   ├── vault/PREFLIGHT-UNSEAL.md          # operator runbook
│   ├── k3s/migrations/0002_audit_tool.sql
│   └── security/                          # NEW
│       ├── INSTALL.md
│       ├── runner-image/Dockerfile
│       ├── runner-scale-set.yaml
│       ├── cluster-image-policy.yaml
│       └── kyverno-policies.yaml
├── scripts/security/build-and-sign-tools.sh
├── tests/
│   ├── unit/test_tool_loop.py             # 6 tests
│   └── security/                          # 4 E2E test files (skip without cluster)
├── docs/WASM-TOOLS-ROADMAP.md
└── claude-code/sprint-6/
    ├── DESIGN.md                          # Approved decisions D1–D10
    └── README.md                          # this file
```

## Day-by-day status

| Day | Task | Status |
|---|---|---|
| 0 (operator) | Vault init/unseal per `PREFLIGHT-UNSEAL.md` | **Blocked on you** |
| 1 | `actions-runner-controller` + `executor.py` + tests | Code done; helm install blocked on cluster |
| 2 | `tools/SDK/` + `parse_dates_v3` source + schema | Code done; `cargo build` blocked on Rust toolchain |
| 3 | `registry.py` + `verifier.py`; integrate into Orchestrator + Analyst | Done |
| 4 | Vault PKI mount + Transit signer; `build-and-sign-tools.sh` | Script done; Vault setup blocked on cluster |
| 5 | sigstore/policy-controller install + rebuild signed images | YAML done; install blocked on cluster |
| 6 | Kyverno install + ClusterPolicies | YAML done; install blocked on cluster |
| 7 | Per-agent NetworkPolicy + Role/RoleBinding | **TODO** — generate from `capabilities.yaml`; depends on cluster |
| 8 | Patch agent Deployments with hardened securityContext | **TODO** — depends on Kyverno being live to validate |
| 9 | `tests/security/*` execution | Scaffolded; runs when cluster + policies are live |
| 10 | Trivy + pen-test + audit report | **TODO** — needs all of the above |

## Run locally

### Verify the offline build (no cluster, no Rust)

```bash
pip install -r requirements-dev.txt
pytest tests/unit services/*/tests services/tool_sandbox/tests -m unit -v
# Expected: 61 passed (with echo.wasm fixture present in
# services/tool_sandbox/tests/fixtures/)
```

If `echo.wasm` is missing, generate it (no wat2wasm install needed — uses wasmtime-py):

```bash
python -c "
import wasmtime, pathlib
wat = pathlib.Path('services/tool_sandbox/tests/fixtures/echo.wat').read_text()
pathlib.Path('services/tool_sandbox/tests/fixtures/echo.wasm').write_bytes(wasmtime.wat2wasm(wat))
"
```

### Build the first real WASM tool (needs Rust)

```bash
rustup target add wasm32-wasip1
bash scripts/security/build-and-sign-tools.sh COSIGN_TEST_MODE=1
# Produces tools/parse_dates_v3/dist/parse_dates_v3.wasm + .sig
```

### Run security E2E tests (needs cluster + Sprint 6 policies applied)

```bash
export KUBECONFIG=~/.kube/aia-config.yaml
pytest tests/security -m security -v
# Without cluster: all tests skip cleanly with clear reason.
# With cluster + policies: tests fail-then-fix-then-retry until cluster is hardened.
```

## Deploy to Hetzner

Order matters. Each step has a verification gate before the next.

1. **Vault preflight** — `infrastructure/vault/PREFLIGHT-UNSEAL.md`
2. **Run sequence in** `infrastructure/security/INSTALL.md`:
   1. Build + push custom runner image
   2. `helm install` actions-runner-controller + scale set
   3. `helm install` sigstore/policy-controller + apply `cluster-image-policy.yaml`
   4. `helm install` kyverno + apply `kyverno-policies.yaml`
3. **Migrate audit_log** — `infrastructure/k3s/migrations/0002_audit_tool.sql`
4. **Apply `llm-api-keys` Secret** if not already present (Sprint 2 dep)
5. **CI build-images job** signs and pushes all 4 agent images
6. **kubectl apply** the agent deployments
7. **Run `pytest tests/security -m security`** — must all pass to declare Sprint 6 done

## Sprint 6 acceptance checklist

- [x] WASM executor enforces fuel + memory + wall-timeout
- [x] Verifier matches cosign-format ECDSA-P256-SHA256
- [x] Registry refuses unknown tools, unauthorized agents, invalid signatures
- [x] Schema validation gates both input and output
- [x] Audit adapter writes one row per tool call with input/output SHA-256
- [x] Rust SDK + 1 reference tool source code
- [x] Cluster-install YAML drafted (ARC + sigstore + Kyverno)
- [x] Security E2E tests scaffolded with clean skip behavior
- [x] CI matrix builds + signs all 4 agent images
- [x] All offline unit tests pass (61/61)
- [ ] **Cluster install runbook executed** (blocked: operator runs `INSTALL.md`)
- [ ] **parse_dates_v3.wasm built + signed for the first time** (blocked: needs Rust toolchain on a machine)
- [ ] **security E2E tests pass against live cluster** (blocked on cluster install)
- [ ] **Trivy scan + pen-test bundle** (Day 10 — blocked on agent images being live)

## Known gaps into Sprint 7+

- LLM debate loop still deferred (Sprint 2's open item; not Sprint 6 scope)
- Tool catalog has 1 real tool; Sprint 7 inventories agent code and adds more per `docs/WASM-TOOLS-ROADMAP.md`
- Vault auto-unseal deferred to Sprint 8 hardening (manual Shamir for now)
- Cosign key rotation cron is documented but not implemented as a CronJob — Day 10 audit may flag this
- `services/compliance_agent/qdrant_indexer.py` is Sprint 3's untouched stub; integration with the WASM registry happens when Gemini ships Sprint 3
