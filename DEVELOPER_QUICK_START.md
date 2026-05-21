# DEVELOPER_QUICK_START.md: Orientation Guide for Senior Developers

Welcome to Synthetic Enterprise. This guide gets you oriented in 30 minutes.

---

## WHAT IS THIS PROJECT?

**In 30 seconds**: We're building an **AI management team** that orchestrates multiple specialist agents to perform complex professional work (legal drafting, compliance verification, contract analysis). The system is:

- **Event-driven**: Agents communicate asynchronously via Redis message bus
- **Deterministic**: Same input → same output (temperature=0 for all LLM calls)
- **Auditable**: Every decision logged with reasoning
- **Secure**: Wasm sandboxed execution; cryptographic signing
- **Compliant**: UK GDPR, SRA, ICO standards baked in
- **Human-controlled**: Humans make final decisions; AI advises

---

## THE TEAM

### The Agents (Your "Colleagues")

1. **Orchestrator** ("Manager")
   - Role: Task decomposition & routing
   - Doesn't do the heavy work; delegates
   - Maintains global state

2. **Compliance Officer** ("Gatekeeper")
   - Role: Regulatory verification
   - Has VETO power
   - Can block outputs that breach UK law

3. **Domain Analyst** ("Researcher")
   - Role: Research, analysis, evidence gathering
   - Uses RAG (retrieval-augmented generation)
   - Must cite everything

4. **Editor** ("Polish Agent")
   - Role: Formatting, document finalization
   - Converts rough outputs to professional docs
   - Quality control

---

## 5-MINUTE PROJECT TOUR

```
1. User submits request
   ↓
2. Orchestrator parses intent & decomposes into tasks
   ↓
3. Tasks routed to agents via Redis
   ├─ Analyst Agent researches precedents
   ├─ Compliance Officer verifies regulations
   └─ Editor formats results
   ↓
4. Results flow back to Orchestrator
   ↓
5. If conflict (e.g., Analyst approves, Compliance rejects):
   → Escalate to human for decision
   ↓
6. Final output sent to user
   ↓
7. ENTIRE PROCESS LOGGED for audit
```

---

## FILE STRUCTURE (WHAT TO READ)

```
synthetic-enterprise/
│
├── README.md
│   └─ START HERE: Project overview, stack, team structure
│
├── ARCHITECTURE.md
│   └─ Decoupled architecture, event-driven patterns, agent taxonomy
│
├── AGENTS.md ⭐ CRITICAL
│   └─ Agent identities, constraints, operating principles
│       (This is your "constitution" for agent behavior)
│
├── docs/
│   ├── SECURITY_ARCHITECTURE.md
│   │   └─ Zero-Trust, Wasm sandboxing, threat model
│   │
│   ├── REGULATORY_FRAMEWORK.md
│   │   └─ UK compliance, August 2026 readiness
│   │
│   ├── DEPLOYMENT_GUIDE.md (in progress)
│   │   └─ Step-by-step K3s/Talos setup
│   │
│   └── RUNBOOK.md (in progress)
│       └─ Daily operations, troubleshooting
│
├── sprints/
│   ├── SPRINT_1_INFRASTRUCTURE.md
│   │   └─ Weeks 1–2: K3s, Redis, PostgreSQL, Echo Agent
│   │
│   ├── SPRINT_2_ORCHESTRATION.md
│   │   └─ Weeks 3–4: Orchestrator, routing, conflict resolution
│   │
│   └── SPRINT_3_THROUGH_8.md
│       └─ Weeks 5–16: RAG, UI, Wasm, compliance, hardening
│
├── services/
│   ├── orchestrator-agent/
│   ├── compliance-agent/
│   ├── analyst-agent/
│   └── editor-agent/
│
├── libs/
│   ├── communication/          ← Message protocol
│   ├── infrastructure/         ← K3s/Talos manifests
│   ├── evaluation/            ← Testing framework
│   └── tracing/               ← OpenTelemetry setup
│
└── infrastructure/
    ├── terraform/             ← IaC for K3s cluster
    ├── helm-charts/          ← Service deployment
    └── tests/                ← Integration test scripts
```

---

## YOUR ROLE: WHICH SPRINT?

### If You're: **Backend Engineer (Agent Logic)**
1. Read: AGENTS.md (15 min)
2. Read: ARCHITECTURE.md (20 min)
3. Pick a Sprint:
   - **Sprint 1**: Echo Agent skeleton (see SPRINT_1_INFRASTRUCTURE.md, Task 1.6)
   - **Sprint 2**: Orchestrator decomposition logic (SPRINT_2_ORCHESTRATION.md, Task 2.1)
   - **Sprint 3**: Analyst Agent + RAG (SPRINT_3_THROUGH_8.md, Section 3)

### If You're: **DevOps/SRE Engineer**
1. Read: ARCHITECTURE.md (20 min)
2. Read: SECURITY_ARCHITECTURE.md (30 min)
3. Start:
   - **Sprint 1**: Infrastructure provisioning (SPRINT_1_INFRASTRUCTURE.md, Task 1.1–1.2)
   - Create Terraform code for K3s cluster
   - Deploy Redis, PostgreSQL, Jaeger

### If You're: **Full-Stack Engineer (Frontend)**
1. Read: ARCHITECTURE.md (20 min)
2. Read: AGENTS.md sections on "Glass Box" (10 min)
3. Start:
   - **Sprint 4**: WebSocket server + React dashboard (SPRINT_3_THROUGH_8.md, Section "SPRINT 4")

### If You're: **Security Engineer**
1. Read: SECURITY_ARCHITECTURE.md (60 min)
2. Read: REGULATORY_FRAMEWORK.md (30 min)
3. Start:
   - **Sprint 6**: Wasm integration (SPRINT_3_THROUGH_8.md, Section "SPRINT 6")
   - **Sprint 7**: Kill-Switch API + compliance controls (SPRINT_3_THROUGH_8.md, Section "SPRINT 7")

### If You're: **QA / Test Engineer**
1. Read: AGENTS.md (15 min)
2. Read: SPRINT_1_INFRASTRUCTURE.md Integration Tests (20 min)
3. Start:
   - **Sprint 1**: Write integration test for Echo Agent (SPRINT_1_INFRASTRUCTURE.md, Task 1.7)
   - **Sprint 3**: Determinism evals (SPRINT_3_THROUGH_8.md, Section "SPRINT 3.4")

---

## CRITICAL CONSTRAINTS (DO NOT VIOLATE)

### 1. Determinism is Non-Negotiable
```python
# CORRECT
llm = ChatAnthropic(model="claude-sonnet-4", temperature=0)  # ✅ Deterministic

# WRONG
llm = ChatAnthropic(model="claude-sonnet-4", temperature=0.7)  # ❌ Non-deterministic
```

**Why?** If an agent makes the same decision twice with the same input, we must get the same output for audit compliance.

### 2. Agents Do NOT Call Each Other Directly
```python
# WRONG ❌
result = analyst_agent.analyze_contract(contract)  # Direct call

# CORRECT ✅
redis_client.xadd('agent:analyst:tasks', {
    'task_id': task_id,
    'contract': contract
})
# Agent listens for message and processes asynchronously
```

**Why?** Decoupling. If Analyst Pod crashes, Orchestrator doesn't block. Message persists in Redis.

### 3. Every Output Must Be Cited
```python
# WRONG ❌
{
  "finding": "Settlement must include confidentiality clause",
  "source": "General knowledge"
}

# CORRECT ✅
{
  "finding": "Settlement must include confidentiality clause",
  "source": {
    "type": "case_law",
    "case": "Malik v BCCI [1997]",
    "jurisdiction": "UK",
    "section": "Confidentiality precedent"
  }
}
```

**Why?** Regulators ask: "Why did you recommend this?" Without sources, you can't defend the recommendation.

### 4. Compliance Officer Has Veto Power
```python
# The contract says "APPROVED" but Compliance says "REJECTED"?
# → REJECT wins. Compliance Officer's decision stands.
# 
# If you disagree, follow debate protocol:
# 1. Ask Analyst to respond to Compliance concern
# 2. If still unresolved, escalate to human
# 3. Do NOT override Compliance Officer
```

**Why?** Regulatory risk. Compliance Officer is the gatekeeper. Their job is to prevent illegal outputs.

### 5. Data is Ephemeral Per Client
```python
# Client A's data must be mathematically unreachable by Client B
# 
# Implementation:
# - K3s namespace isolation (client_a vs client_b)
# - Milvus partition per client
# - Redis key prefixes: data:client_a:*, data:client_b:*
#
# Testing: Try to query Client B data from Client A agent
# → Must return "access denied"
```

**Why?** GDPR data minimization + UK data sovereignty laws.

---

## TECH STACK QUICK REFERENCE

| Layer | Technology | Why |
|-------|-----------|-----|
| **Language** | Python 3.11 | AI/ML libraries mature; good async support |
| **Orchestration** | LangGraph | Native state graphs; deterministic checkpoints |
| **Message Broker** | Redis | Fast, persistent, pub/sub + streams |
| **Vector DB** | Qdrant (Compliance), Milvus (Analyst) | Isolated, performant, partitionable |
| **LLM** | Claude Sonnet 4 | Best reasoning/cost ratio; temperature=0 |
| **Infrastructure** | Talos + K3s | Immutable OS; self-healing K8s |
| **Security** | WasmEdge + Cosign | Sandboxing + signing |
| **Frontend** | Next.js + React | Real-time WebSocket; modern UX |
| **Observability** | OpenTelemetry + Jaeger | End-to-end tracing |
| **Audit** | PostgreSQL (immutable) | Cryptographically signed logs |

---

## COMMON WORKFLOWS

### Workflow 1: Add a New Tool
```python
# 1. Write tool in Rust (Wasm target)
#    File: tools/new_tool.rs

# 2. Build to Wasm
#    cargo build --target wasm32-unknown-unknown

# 3. Sign with Cosign
#    cosign sign-blob --key infrastructure/cosign/cosign.key tools/new_tool.wasm

# 4. Define capability in agent_capabilities ConfigMap
#    "domain_analyst": { "allowed_tools": [..., "new_tool"] }

# 5. Register in ExecutionEngine
#    executor.register_capability("new_tool", new_tool_fn)

# 6. Write unit + integration tests
#    services/analyst-agent/test_new_tool.py

# 7. Create PR; merge after review
```

### Workflow 2: Update Agent Prompt
```python
# 1. Edit prompt in services/{agent}/prompts.py

# 2. Run determinism tests
#    pytest libs/evaluation/determinism_evals.py -k new_prompt

# 3. If non-deterministic, adjust prompt until deterministic
#    (This may require multiple iterations)

# 4. Run full integration test
#    bash infrastructure/tests/integration_test_full_workflow.sh

# 5. Create PR; requires architect sign-off
```

### Workflow 3: Debug Agent Issue
```bash
# 1. Check agent logs
kubectl logs -f deployment/analyst-agent

# 2. Check OpenTelemetry traces
# Open Jaeger UI (port 16686)
# Search by service: analyst-agent
# Trace the request end-to-end

# 3. Check Redis messages
redis-cli
> XREAD STREAMS agent:analyst:tasks 0

# 4. Check PostgreSQL audit log
psql synthetic_enterprise
# SELECT * FROM audit_log WHERE from_agent = 'analyst' ORDER BY created_at DESC;

# 5. Check agent checkpoints
redis-cli
> GET checkpoint:analyst:*
```

---

## GLOSSARY

| Term | Definition |
|------|-----------|
| **Agent** | Specialized AI service that performs one type of work (Analyst, Compliance, etc.) |
| **Task** | Unit of work assigned to an agent (e.g., "review this contract") |
| **Task Graph** | DAG of all tasks for a project, showing dependencies |
| **RAG** | Retrieval-Augmented Generation: AI that searches knowledge bases before answering |
| **Checkpoint** | Saved agent state at specific point; allows recovery after crash |
| **Escalation** | When agent encounters high-risk decision, asks human |
| **Approval Gate** | UI where human can approve/reject escalated decision |
| **Decision Log** | Immutable record of why agent made each decision |
| **Wasm** | WebAssembly: sandboxed bytecode that runs in isolated memory |
| **Cosign** | Tool for cryptographically signing software artifacts |
| **Namespace** | K3s isolation unit for per-client sandboxing |
| **OpenTelemetry** | Standard for distributed tracing across services |

---

## FIRST DAY TASKS

Pick ONE of these based on your role:

### Backend Engineer
```bash
# 1. Clone repo
git clone <repo-url>
cd synthetic-enterprise

# 2. Read AGENTS.md (15 min)
# 3. Read ARCHITECTURE.md (20 min)

# 4. Pick an agent to implement
# Example: services/echo-agent/main.py (from SPRINT_1)

# 5. Write skeleton code
# Use the prompt template from AGENTS.md

# 6. Write unit tests
# pytest services/echo-agent/test_agent.py -v

# 7. Create PR with "Draft" status
# PR Title: "Draft: Echo Agent Implementation"
```

### DevOps Engineer
```bash
# 1. Read ARCHITECTURE.md (20 min)
# 2. Read SPRINT_1_INFRASTRUCTURE.md Task 1.1 (30 min)

# 3. Create Terraform code
# File: infrastructure/terraform/main.tf

# 4. Provision K3s cluster
# terraform apply

# 5. Verify cluster health
# kubectl get nodes

# 6. Create PR with "Draft" status
```

### Frontend Engineer
```bash
# 1. Read ARCHITECTURE.md (20 min)
# 2. Skim SPRINT_4_GLASS_BOX_UI.md

# 3. Create Next.js project
# npx create-next-app web-dashboard --typescript

# 4. Implement WebSocket connection
# (Connect to Orchestrator via ws://localhost:8000/ws/{projectId})

# 5. Implement AgentMonitor component
# Show real-time agent status

# 6. Create PR with "Draft" status
```

---

## GETTING HELP

### Code Questions
- Grep AGENTS.md for your agent's operating constraints
- Grep ARCHITECTURE.md for pattern examples
- Check existing agent implementations in services/

### Architectural Questions
- Ask architect (Lead Backend Engineer) synchronously
- Post in #architecture Slack channel
- Reference ARCHITECTURE.md when asking

### Operational Questions
- Check docs/RUNBOOK.md (when available)
- Ask DevOps engineer
- Review SPRINT_1_INFRASTRUCTURE.md troubleshooting section

### Regulatory/Compliance Questions
- Check docs/REGULATORY_FRAMEWORK.md
- Ask Security Engineer
- Reference SRA principles if legal work involved

---

## SUCCESS CRITERIA FOR YOUR FIRST WEEK

- ✅ Understand the 4-agent model (Orchestrator, Compliance, Analyst, Editor)
- ✅ Know why determinism matters
- ✅ Know your role in the sprint plan
- ✅ Have read AGENTS.md (at least your agent's section)
- ✅ Have cloned repo + set up dev environment
- ✅ Have created your first PR (even if "Draft" status)

---

**Next Steps**: Pick your sprint from SPRINT_1_INFRASTRUCTURE.md, SPRINT_2_ORCHESTRATION.md, or SPRINT_3_THROUGH_8.md. The specific task will be waiting for you there.

Welcome to the team. 🚀

