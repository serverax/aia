# Sprint 6 Design — WASM Security Layer

**Status:** Draft, awaiting approval
**Author:** Claude Code
**Target start:** Week 12
**Locks in before code starts:** the three decisions in [§ Decisions log](#decisions-log), the file layout in [§ Layout](#layout), and the Day-by-day implementation order in [§ Implementation order](#implementation-order).

---

## Decisions log

| # | Question | Decision | Rationale |
|---|---|---|---|
| D1 | What runs in WASM? | **Tool calls only.** Agents stay Python/FastAPI. | Agents need OS sockets (Redis, Postgres, OTLP) and async I/O that aren't available in WASI. The actual attack surface is LLM-generated code, not the agent runtime. |
| D2 | Signature admission controller | **sigstore/policy-controller** | Purpose-built for Cosign; lighter than Kyverno/OPA for signature-only verification. Kyverno still used for capability policies (D3). |
| D3 | Capability enforcement primitive | **NetworkPolicy + RBAC + Kyverno** (three layers) | Native K8s primitives where possible; Kyverno only for cross-cutting rules. Cilium ruled out as over-scoped. |
| D4 | WASM runtime | **wasmtime-py 24.x** | Mature Python bindings (`pip install wasmtime`), CNCF graduated, fuel metering + memory limits in stable API. WasmEdge stays as a future swap option — module-level portability via WASI keeps us free. |
| D5 | Tool source language | **Rust → wasm32-wasip1** as default; second-class support for **JS-in-WASM** (QuickJS) if a tool needs to evaluate small templated expressions. | Rust gives strict typing for the curated tool registry. QuickJS gives a path for safe expression eval without exposing eval(). |
| D6 | Tool authoring model | **Curated registry of pre-built, pre-signed tools** the LLM picks from by name (with typed params). Arbitrary LLM-generated code execution is **OUT of Sprint 6 scope.** | This is what every production "tool use" system does in 2026 (Claude tool-use, OpenAI tools, Bedrock agents). Sandboxing arbitrary LLM-written code is a Sprint 7+ research project, not a 2-week sprint. |
| D7 | Cosign key custody | **Vault PKI mount** issues a Cosign-compatible key pair per environment (dev / staging / prod). 30-day rotation via cron + admission policy update. | Centralized custody, audited issuance, no plaintext keys on disk. |
| D8 | CI build + sign host | **Self-hosted GHA runner pod inside the K3s cluster** via `actions-runner-controller`. | Vault stays internal-only (no public ingress, no mTLS tunnel). Runner reaches Vault via `vault.vault.svc.cluster.local`. Trade: lose hosted-runner minutes; gain Vault network isolation + deterministic cluster-resident builds. |
| D9 | Vault init + unseal | **Manual preflight by operator** before Sprint 6 Day 1. See `infrastructure/vault/PREFLIGHT-UNSEAL.md`. Auto-unseal deferred to Sprint 8. | Hetzner has no native cloud KMS; Transit-on-Vault doubles ops surface; Shamir manual unseal is acceptable for one-off restarts. |
| D10 | Sprint 6 tool catalog scope | **Three reference tools only** (`parse_dates_v3`, `extract_citations_v1`, `validate_regulation_v1`). Business catalog deferred to Sprint 7+ per `docs/WASM-TOOLS-ROADMAP.md`. | 10-day budget; security infra is the load-bearing deliverable; tool needs depend on Sprint 3/5 agent inventory we don't have yet. |

---

## D1. WASM scope: tool-only, not agents

### Problem

Sprint 6 spec text says "Sandbox all agent-generated code execution. Cryptographic signing of all Wasm modules." The spec also shows `wasmtime.Module(...)` executing `agent_tool.wasm` — clearly tool-level, not agent-level. But the Sprint 6 deliverable bullets ("Compile Echo Agent → WASM") suggest whole-agent compilation. That isn't viable: CPython doesn't target WASM, and our agents use OS sockets for Redis Streams, Postgres, OTLP, and FastAPI.

### Decision

- **Agents stay as Python/FastAPI services** running in regular Linux containers (already deployed in Sprints 1–2).
- **Tool calls execute in WASM.** A "tool call" is a discrete, bounded computation the LLM asks an agent to perform: parse a contract clause, validate a regulation citation, run a deterministic risk-score formula, render a date range. These are pure functions over typed inputs.
- **Tool source code lives in `tools/` (NEW root-level dir)**, gets compiled to WASM, signed with Cosign, published to the artifact registry, and resolved at runtime by name.

### Trust boundary

```
┌─────────────────────────────────────────────────────────────┐
│  Agent process (trusted)                                    │
│  ──────────────────────                                     │
│   - Talks to Redis, Postgres, Jaeger, Claude API            │
│   - Receives "tool_use" responses from Claude               │
│   - For each tool_use: looks up `tool_id` in signed registry│
│   - Loads .wasm into wasmtime sandbox                       │
│   - Passes typed params, awaits typed result                │
│  ────────────────────────────────────────────┐              │
│                                              │              │
│      ┌───────────────────────────────────┐   │              │
│      │  WASM sandbox (untrusted)         │ ◄─┘ JSON in/out  │
│      │  ───────────────────────          │                  │
│      │   - No filesystem access          │                  │
│      │   - No network access (denied)    │                  │
│      │   - Memory cap (64 MiB)           │                  │
│      │   - CPU cap (fuel = ~100ms)       │                  │
│      │   - WASI imports: stdin/stdout    │                  │
│      │     and clock_get only            │                  │
│      └───────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### Tool execution flow

```
1. Analyst Agent (Python) sends prompt with tools spec to Claude
2. Claude returns tool_use block: { id: "parse_dates_v3", input: {...} }
3. Agent looks up "parse_dates_v3" in services/tool_sandbox/registry
4. Agent verifies Cosign signature on the cached .wasm file
   - if missing/invalid → refuse + record audit row
5. Agent instantiates wasmtime engine with limits
6. Agent passes input JSON via wasi stdin
7. WASM module runs (≤ 64 MiB, ≤ 100ms CPU fuel)
8. Output JSON read from wasi stdout
9. Agent parses, validates against tool's output schema
10. Agent sends result back to Claude in next message
```

---

## D2. Admission controller: sigstore/policy-controller

### Setup

```
helm repo add sigstore https://sigstore.github.io/helm-charts
helm install policy-controller sigstore/policy-controller \
    --namespace cosign-system --create-namespace \
    --set webhook.image.tag=v0.10.2
```

### Policy

A single `ClusterImagePolicy` enforces that any image whose name matches our
GHCR prefix MUST carry a Cosign signature against the Vault-issued public key.

```yaml
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata:
  name: aia-images-must-be-signed
spec:
  images:
    - glob: "ghcr.io/serverax/aia/**"
  authorities:
    - name: aia-cosign-key
      key:
        # PEM body is fetched from Vault by an init job that writes it into
        # this ConfigMap. Rotation = update ConfigMap + bump version label.
        secretRef:
          name: aia-cosign-pubkey
          namespace: cosign-system
```

### Where the .wasm files fit

`.wasm` artifacts aren't OCI images, so policy-controller doesn't gate them
directly. Instead:

- **At publish time** (CI): `cosign sign-blob` writes a `.sig` next to each `.wasm` in the OCI artifact registry.
- **At load time** (agent): the `WasmRegistry` class verifies `.sig` against the public key fetched from `cosign-system/aia-cosign-pubkey` before instantiating.

This puts the verification on the *runtime hot path* where it actually
protects code execution, not just pod admission.

---

## D3. Capability enforcement: NetworkPolicy + RBAC + Kyverno

### Layer 1 — NetworkPolicy (already partial in Sprint 1 namespace.yaml)

Each agent gets a `NetworkPolicy` that allows only:
- Egress to Postgres + Redis services in the same namespace
- Egress to `kube-dns` (UDP/TCP 53)
- Egress to Jaeger
- Egress to `api.anthropic.com:443` (only for agents that talk to the LLM — Orchestrator, Analyst; Echo and Compliance get no external egress)
- Ingress on the agent's `http` port from the cluster ingress controller only

### Layer 2 — RBAC

One `ServiceAccount` per agent, each bound to a `Role` whose verbs and
resources mirror the capability matrix below. No agent gets `secrets`
verbs except for its own `*-credentials` Secret.

### Layer 3 — Kyverno cross-cutting policies

Kyverno enforces invariants no single agent should opt out of:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: aia-pod-hardening
spec:
  validationFailureAction: Enforce
  rules:
    - name: read-only-root-fs
      match:
        any: [{ resources: { namespaces: ["synthetic-enterprise"] } }]
      validate:
        message: "Pods in synthetic-enterprise must use read-only root filesystem"
        pattern:
          spec:
            containers:
              - securityContext:
                  readOnlyRootFilesystem: true
                  allowPrivilegeEscalation: false
                  runAsNonRoot: true
    - name: drop-all-caps
      match:
        any: [{ resources: { namespaces: ["synthetic-enterprise"] } }]
      validate:
        message: "Containers must drop ALL Linux capabilities"
        pattern:
          spec:
            containers:
              - securityContext:
                  capabilities:
                    drop: ["ALL"]
    - name: no-host-mounts
      match:
        any: [{ resources: { namespaces: ["synthetic-enterprise"] } }]
      validate:
        message: "Host path volumes are forbidden"
        deny:
          conditions:
            - key: "{{ request.object.spec.volumes[].hostPath }}"
              operator: AnyIn
              value: ["?*"]
```

### Capability matrix (source of truth)

`infrastructure/security/capabilities.yaml` — referenced by code review; not
applied directly (it drives the generation of the per-agent NetworkPolicy +
RBAC files).

```yaml
agents:
  echo:
    network:
      egress_allow: [redis, postgres, jaeger]
      egress_deny: [internet, anthropic]
    rbac:
      secrets: [postgres-credentials]
      configmaps: [echo-agent-config]
    fs: { root: read-only, writable: [/tmp] }

  orchestrator:
    network:
      egress_allow: [redis, postgres, jaeger, "api.anthropic.com:443"]
    rbac:
      secrets: [postgres-credentials, llm-api-keys]
      configmaps: [orchestrator-agent-config]
    fs: { root: read-only, writable: [/tmp] }

  compliance:
    network:
      egress_allow: [redis, postgres, jaeger, qdrant]
    rbac:
      secrets: [postgres-credentials]
      configmaps: [compliance-agent-config]
    fs: { root: read-only, writable: [/tmp] }

  analyst:
    network:
      egress_allow: [redis, postgres, jaeger, milvus, qdrant, "api.anthropic.com:443"]
    rbac:
      secrets: [postgres-credentials, llm-api-keys]
    fs: { root: read-only, writable: [/tmp] }
```

---

## D4 + D5 + D6. WASM runtime, tool source language, tool authoring model

### Runtime: wasmtime-py 24.x

```python
from wasmtime import Engine, Module, Store, Config, WasiConfig, Linker

config = Config()
config.consume_fuel = True
config.epoch_interruption = True   # cooperative deadlines
engine = Engine(config)

store = Store(engine)
store.set_fuel(100_000_000)        # ~100ms on a typical CPU
store.set_epoch_deadline(1)

linker = Linker(engine)
linker.define_wasi()

wasi = WasiConfig()
wasi.inherit_stdout = False        # capture instead
wasi.inherit_stderr = False
wasi.inherit_env = False           # no env leak
# NO preopened_dir, NO inherit_network — zero ambient authority

store.set_wasi(wasi)
```

Memory is bounded at module level (`(memory $mem 1024)` = 64 MiB; Rust
tools must declare this in their `wasm32-wasip1` target config) and
checked at instantiation time.

### Tool source: Rust as default

Each tool lives in `tools/<tool_name>/` as a Rust crate that compiles to a
single WASM module reading JSON from stdin and writing JSON to stdout. A
small `tools/SDK/` crate provides the input/output helpers so individual
tool authors write only the pure logic.

```
tools/parse_dates_v3/
├── Cargo.toml
├── src/lib.rs         # the actual logic
├── schema.json        # input + output JSON Schema (machine-readable contract)
└── tool.yaml          # name, version, allowed_agents, capability_class
```

### Authoring model: curated registry

LLMs **do not** write arbitrary code that we then compile. Instead:

1. Each agent advertises a fixed set of tools to Claude as part of its prompt:
   `[{ "name": "parse_dates_v3", "description": "...", "input_schema": {...} }]`
2. Claude responds with `tool_use` containing `name` + `input`.
3. The agent's `ToolRegistry` resolves the name to a signed `.wasm` blob, verifies, and executes.
4. Output goes back to Claude in the next message.

This is the same pattern as Anthropic's Claude tool use, OpenAI's tools,
and Bedrock Agents. It's the only model where the audit story holds up
(every tool's source code is in git, every binary is signed, the LLM only
picks from an approved list).

### What about LLM-written code?

Out of scope for Sprint 6. If business needs it later, the path is:
1. The LLM generates code in a `code_interpreter`-style tool whose body itself runs in the same WASM sandbox (so the user gets sandbox-on-sandbox).
2. Inputs/outputs constrained to JSON.
3. Network and filesystem still denied.

Sprint 7 or later.

---

## D7. Cosign keys via Vault PKI

```
# One-time bootstrap (manual, post-cluster-provisioning)
vault secrets enable -path=cosign pki
vault write cosign/root/generate/internal \
    common_name="aia-cosign-root" ttl=8760h

# Per-environment signing key
vault write cosign/issue/aia-cosign \
    common_name="cosign-prod" ttl=720h    # 30 days

# Cosign signs with the issued key
cosign sign-blob \
    --key vault://cosign/prod \
    tools/parse_dates_v3/target/wasm32-wasip1/release/parse_dates_v3.wasm \
    > parse_dates_v3.wasm.sig
```

Rotation is a CronJob in `cosign-system` that:
1. Calls `vault write cosign/issue/aia-cosign ...` to get a new keypair.
2. Pushes the new public key into `cosign-system/aia-cosign-pubkey` ConfigMap.
3. Re-signs all current `.wasm` artifacts with the new key.
4. Bumps the policy version annotation.

---

## Layout

```
F:\aia\
├── services/tool_sandbox/                  # NEW — Python wrapper used by agents
│   ├── __init__.py
│   ├── registry.py                         # ToolRegistry: name → signed .wasm
│   ├── executor.py                         # wasmtime engine, limits, JSON I/O
│   ├── policies.py                         # which agents may call which tools
│   ├── verifier.py                         # cosign signature verification
│   ├── requirements.txt
│   └── tests/
│       ├── test_registry.py
│       ├── test_executor.py
│       └── test_verifier.py
│
├── tools/                                  # NEW root — actual WASM tool source
│   ├── README.md
│   ├── SDK/                                # shared Rust crate for json I/O
│   │   ├── Cargo.toml
│   │   └── src/lib.rs
│   ├── parse_dates_v3/
│   │   ├── Cargo.toml
│   │   ├── src/lib.rs
│   │   ├── schema.json
│   │   └── tool.yaml
│   ├── extract_citations_v1/
│   │   └── ...
│   └── validate_regulation_v1/
│       └── ...
│
├── infrastructure/security/                # NEW
│   ├── policy-controller-install.yaml      # sigstore install + ClusterImagePolicy
│   ├── kyverno-install.yaml                # Kyverno install + ClusterPolicies
│   ├── vault-cosign-bootstrap.sh           # one-shot Vault setup
│   ├── rotate-cosign-key.sh                # 30-day rotation script
│   └── capabilities.yaml                   # source-of-truth capability matrix
│
├── infrastructure/k3s/
│   ├── network-policies-per-agent.yaml     # NEW — generated from capabilities.yaml
│   ├── rbac-per-agent.yaml                 # NEW — generated from capabilities.yaml
│   └── agent-deployments-hardened.yaml     # NEW — securityContext patches
│
├── scripts/security/                        # NEW
│   ├── build-and-sign-tools.sh             # build all WASM + cosign sign
│   ├── verify-all-signatures.sh            # CI gate
│   ├── trivy-scan-images.sh                # image vuln scan
│   └── pen-test-bundle.sh                  # OWASP ZAP baseline
│
└── tests/security/                          # NEW
    ├── test_admission_rejects_unsigned.py  # E2E: try to deploy unsigned image
    ├── test_kyverno_blocks_writable_root.py
    └── test_networkpolicy_blocks_external.py
```

---

## Implementation order

Day 0 = your preflight (Vault init+unseal per `infrastructure/vault/PREFLIGHT-UNSEAL.md`).

| Day | Task | Output |
|---|---|---|
| 1 | `actions-runner-controller` Helm install + runner pod with rust/cosign/vault-CLI image; `services/tool_sandbox/executor.py` + unit tests against a hand-written hello-world `.wasm` | CI runner reachable from `runs-on: [self-hosted, k3s]`; can execute any WASI module with limits |
| 2 | `tools/SDK/` + `tools/parse_dates_v3/` reference implementation; build + run via executor | First real tool works end-to-end |
| 3 | `services/tool_sandbox/registry.py` + `verifier.py`; integrate into Orchestrator and Analyst agents | Agents can pick + run tools from registry |
| 4 | Vault PKI mount + Transit signer setup (root token used + then revoked, app-scoped token issued per `PREFLIGHT-UNSEAL.md`); `scripts/security/build-and-sign-tools.sh` runs on the cluster runner | Signed tool artifacts published, no Vault network exposure |
| 5 | sigstore/policy-controller install + `ClusterImagePolicy`; rebuild + sign all agent images via the self-hosted runner | All agent images deploy only if signed |
| 6 | Kyverno install + ClusterPolicies (read-only fs, no host mounts, drop caps) | Cluster-wide pod hardening enforced |
| 7 | Per-agent `NetworkPolicy` + `Role/RoleBinding` files (generated from `capabilities.yaml`) | Each agent limited to its declared capabilities |
| 8 | Patch existing agent Deployments with hardened `securityContext` (read-only root + capability drops + non-root UID); ship `tools/extract_citations_v1/` and `tools/validate_regulation_v1/` (the other two reference tools) | All agents pass Kyverno admission; three reference tools shipped per `docs/WASM-TOOLS-ROADMAP.md` |
| 9 | `tests/security/*` — admission rejects unsigned images; Kyverno blocks bad pods; NetworkPolicy blocks egress | E2E security guarantees verified |
| 10 | `trivy-scan-images.sh` + `pen-test-bundle.sh` + audit report markdown | Sprint 6 audit deliverable |

---

## Tests strategy

| Layer | What's tested | How |
|---|---|---|
| Unit | `executor.py` enforces fuel + memory + WASI denials | wasmtime test fixtures, no docker |
| Unit | `verifier.py` rejects tampered `.wasm` | known-good + corrupted blob pairs |
| Unit | `registry.py` rejects unknown tool names + version mismatches | in-memory registry fixtures |
| Integration | A real Rust tool compiles, signs, loads, runs | docker-compose adds a `wasm-build` job-style container |
| Security (E2E) | Deploying unsigned image is rejected by sigstore | uses local kind cluster + `kubectl apply` returning non-zero |
| Security (E2E) | Pod with writable root FS is rejected by Kyverno | same |
| Security (E2E) | Agent pod cannot reach `1.1.1.1` (external) | exec into pod, curl, expect timeout |

---

## What's out of scope

- **Arbitrary LLM-written code execution.** Curated tools only.
- **GPU-bound tools.** WASI doesn't have a GPU story yet; defer.
- **Long-running tools (> 100 ms CPU).** Hard limit per execution.
- **Tools with filesystem persistence.** Tools are stateless functions.
- **Multi-tenant key isolation.** Per-environment keys, not per-tenant.
- **Hardware attestation (TPM / TEE).** Future hardening.
- **Cilium / eBPF L7 policies.** NetworkPolicy + Kyverno covers our model.
- **LLM debate / negotiation between agents.** Sprint 2 deferred this; still deferred.

---

## Week 12 readiness checklist

When you ping me to start Sprint 6:

- [ ] This DESIGN.md is approved verbatim (or with marked diffs)
- [ ] `provision-cluster-full.sh` has been run successfully — namespace `synthetic-enterprise` exists
- [ ] **Vault preflight done** — `infrastructure/vault/PREFLIGHT-UNSEAL.md` followed; `vault status` shows `Sealed: false`; `~/.aia/secrets/vault-init.json` exists with 600 perms
- [ ] `ANTHROPIC_API_KEY` is set in `llm-api-keys` Secret (from Sprint 2)
- [ ] You've confirmed which agents (from Sprints 3, 4, 5) actually use tools — currently the design assumes Orchestrator + Analyst do, Echo + Editor don't. If that's wrong, the capability matrix changes.

When that's all true, Day 1 begins.

---

## Answers locked (post-review)

| Question | Locked answer | Reference |
|---|---|---|
| Q1 — CI build/sign host | Self-hosted GHA runner pod inside K3s via `actions-runner-controller`. Runner reaches Vault via in-cluster DNS; no public Vault ingress. | DESIGN.md § D8; Day 1 of implementation order |
| Q2 — Vault unseal | Manual preflight by operator; Sprint 6 starts with Vault unsealed. Auto-unseal deferred to Sprint 8. | `infrastructure/vault/PREFLIGHT-UNSEAL.md`; DESIGN.md § D9 |
| Q3 — Tool catalog scope | Three reference tools only in Sprint 6 (`parse_dates_v3`, `extract_citations_v1`, `validate_regulation_v1`). Business catalog comes in Sprint 7+ as agents declare need. | `docs/WASM-TOOLS-ROADMAP.md`; DESIGN.md § D10 |

No open questions remain. Sprint 6 is fully locked.

---

**End of design. Ready for review.**
