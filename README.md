# Synthetic Enterprise: Hierarchical Multi-Agent Orchestration Platform

## Project Status: BUILD PHASE (Weeks 1-16)

A production-grade, regulatory-compliant, multi-agent orchestration engine designed for UK professional services (law, cybersecurity, compliance). This is not a chatbot. This is a **synthetic management team** that reasons, debates, and produces auditable professional outputs.

---

## MISSION STATEMENT

Build a **Zero-Trust, Event-Driven, Hierarchical Multi-Agent System** that orchestrates specialized AI agents to perform complex professional work while maintaining:

- **Absolute data sovereignty** (client data never leaves your infrastructure)
- **Full auditability** (every decision traceable to its rationale)
- **Regulatory compliance** (UK GDPR, Employment Law, SRA, ICO standards)
- **Human-in-the-loop control** (critical decisions require explicit approval)
- **Architectural security** (Wasm-sandboxed execution, capability-based permissions)

---

## PROJECT STRUCTURE

```
/synthetic-enterprise/
│
├── README.md                           # This file
├── ARCHITECTURE.md                     # High-level design patterns
├── AGENTS.md                          # Agent taxonomy & operating principles
│
├── docs/
│   ├── REGULATORY_FRAMEWORK.md        # UK compliance requirements
│   ├── SECURITY_ARCHITECTURE.md       # Zero-Trust, Wasm, signing
│   ├── DEPLOYMENT_GUIDE.md            # Talos/K3s setup instructions
│   ├── API_SPECIFICATION.md           # OpenAPI/JSON-RPC specs
│   └── DECISION_RECORDS.md            # Architecture Decision Records (ADRs)
│
├── sprints/
│   ├── SPRINT_1_INFRASTRUCTURE.md     # Infrastructure & core loop
│   ├── SPRINT_2_ORCHESTRATION.md      # Multi-agent routing
│   ├── SPRINT_3_RAG_KNOWLEDGE.md      # Vector DBs & tool integration
│   ├── SPRINT_4_GLASS_BOX_UI.md       # Frontend & real-time updates
│   ├── SPRINT_5_EDITOR_POLISH.md      # Document finalization
│   ├── SPRINT_6_WASM_SECURITY.md      # Wasm sandboxing & signing
│   ├── SPRINT_7_COMPLIANCE_LAYER.md   # Regulatory controls
│   └── SPRINT_8_HARDENING.md          # Load testing & production prep
│
├── apps/
│   ├── web-dashboard/                 # Next.js React frontend
│   └── api-gateway/                   # FastAPI entry point
│
├── services/
│   ├── orchestrator-service/          # Task decomposition & routing
│   ├── compliance-agent/              # Regulatory verification
│   ├── analyst-agent/                 # RAG & domain reasoning
│   └── finalizer-agent/               # Document formatting
│
├── libs/
│   ├── communication/                 # Message protocol & schemas
│   ├── infrastructure/                # K3s/Talos manifests
│   ├── evaluation/                    # Testing & hallucination checks
│   └── tracing/                       # OpenTelemetry instrumentation
│
├── infrastructure/
│   ├── terraform/                     # IaC for K3s cluster
│   ├── helm-charts/                   # Service deployment configs
│   └── talos-configs/                 # Node bootstrap configs
│
└── .gitignore
```

---

## QUICK START FOR DEVELOPERS

### Phase 1: Read (Mandatory)
1. Read **ARCHITECTURE.md** (30 min)
2. Read **AGENTS.md** (15 min) — This is your "Employee Handbook"
3. Skim **docs/SECURITY_ARCHITECTURE.md** (20 min)

### Phase 2: Setup (Day 1)
1. Clone this repo
2. Run `scripts/bootstrap.sh` to provision K3s cluster and Redis broker
3. Deploy skeleton services using Helm
4. Run integration tests to verify message bus

### Phase 3: Develop (Weekly)
- Follow the active Sprint guide (e.g., SPRINT_1_INFRASTRUCTURE.md)
- Each sprint has specific, testable deliverables
- Push changes to feature branches; open PRs against main
- Automated CI/CD tests all code before merge

---

## TECHNICAL STACK AT A GLANCE

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11 (primary), Go (optional) | AI tooling mature in Python; Go for performance-critical paths |
| **Orchestration** | LangGraph (state graphs) | Native support for deterministic checkpoints & audit trails |
| **Message Broker** | Redis (MVP), Kafka (scale) | Async communication; decouples agents |
| **Vector DB** | Qdrant (Compliance), Milvus (Domain) | Isolated, client-partitioned knowledge |
| **Inference** | Claude Sonnet 4 (primary), LiteLLM proxy | Cost-efficient, reliable; model agnostic routing |
| **Infrastructure** | Talos Linux + K3s | Immutable OS; self-healing Kubernetes |
| **Security** | WasmEdge + Cosign signing | Capability-based sandboxing; artifact attestation |
| **Frontend** | Next.js + React | Real-time WebSocket updates; modern UX |
| **Observability** | OpenTelemetry + Prometheus + Grafana | Full distributed tracing; cost monitoring |
| **Audit Log** | PostgreSQL (immutable append-only) | Cryptographically signed event log |

---

## CRITICAL NON-NEGOTIABLE PRINCIPLES

### 1. **Decoupled Architecture**
- Infrastructure (K3s/Talos) manages WHERE things run.
- Orchestration (LangGraph) manages WHAT they do.
- **Never** build a monolithic "Master Algorithm."

### 2. **Event-Driven Communication**
- Agents do NOT call each other's functions directly.
- All agent-to-agent communication flows through Redis message bus.
- Structured JSON payloads with `task_id`, `status`, `data`, `rationale`.

### 3. **Deterministic Workflows**
- Critical paths (legal drafting, compliance checks) use state machines.
- Every decision must be reproducible (temperature=0 for LLM calls).
- Checkpoints allow recovery from mid-workflow crashes.

### 4. **Data Sovereignty**
- Each client gets isolated Kubernetes namespace.
- Vector DB partitions per client (no cross-tenant data leakage).
- All data is ephemeral; deleted after project completion.

### 5. **Full Auditability**
- Every agent action logged with rationale.
- Immutable PostgreSQL audit log (cryptographically signed).
- "Decision Log" shows exactly why the AI made each decision.

### 6. **Zero-Trust Security**
- All agent-generated code runs in WasmEdge sandbox.
- Capability-based permissions (deny-all default).
- OCI artifacts signed with Cosign; signature verified before execution.

---

## SPRINT OVERVIEW (16 WEEKS)

| Sprint | Duration | Focus | Key Deliverable |
|--------|----------|-------|-----------------|
| **1** | Weeks 1–2 | Infrastructure & message bus | Echo Agent through Redis; baseline observability |
| **2** | Weeks 3–4 | Orchestrator & routing | Multi-agent workflow; task decomposition |
| **3** | Weeks 5–7 | RAG & knowledge | Compliance DB + Domain KB; tools working |
| **4** | Weeks 8–9 | Frontend & human-in-the-loop | Glass Box UI; approval gates functional |
| **5** | Weeks 10–11 | Document finalization & polish | Editor Agent; DOCX/PDF generation working |
| **6** | Weeks 12–13 | Wasm security layer | All agent-tools sandboxed; signatures verified |
| **7** | Weeks 14–15 | Compliance controls | Kill-Switch API; containment middleware |
| **8** | Week 16 | Hardening & launch prep | Load testing; SLA defined; ready for market |

---

## DEPENDENCIES & ASSUMPTIONS

### Hardware (Minimum for MVP)
- 3× bare-metal nodes (64GB RAM, 8-core CPU, NVMe SSD)
- Estimated cost: £3k–5k/month (Hetzner, Linode Metal, or on-premises)

### Accounts & API Keys
- Anthropic API (Claude Sonnet 4 access)
- GitHub Container Registry (OCI artifact storage)
- DuckDuckGo API (web search)
- LexisNexis/Westlaw feed (case law, optional for MVP)

### Team Composition
- 1 Senior Architect (directs decisions, owns design)
- 2 Backend Engineers (agent logic + state management)
- 1 DevOps/SRE Engineer (infrastructure + observability)
- 1 Data Engineer (RAG pipelines)
- 1 Full-Stack Engineer (frontend + WebSocket)
- 1 Security Engineer (Wasm, signing, threat modeling)
- 1 QA Engineer (evals, load testing, documentation)

---

## HOW TO READ THIS DOCUMENTATION

**For Architects**: Start with ARCHITECTURE.md → SECURITY_ARCHITECTURE.md → Individual Sprint Technical Briefs

**For Backend Engineers**: Start with AGENTS.md → SPRINT_1_INFRASTRUCTURE.md → Follow your assigned sprint sequentially

**For DevOps/SRE**: Start with ARCHITECTURE.md → DEPLOYMENT_GUIDE.md → infrastructure/ directory

**For Frontend**: Start with AGENTS.md → SPRINT_4_GLASS_BOX_UI.md → apps/web-dashboard/README.md

**For Security**: Start with SECURITY_ARCHITECTURE.md → SPRINT_6_WASM_SECURITY.md → docs/DECISION_RECORDS.md

---

## SUCCESS CRITERIA

### Technical Metrics
- ✅ **Accuracy**: >95% of outputs pass compliance review without revision
- ✅ **Speed**: <60 seconds end-to-end latency (user request → final output)
- ✅ **Uptime**: 99.5%+ availability (measured over 30 days)
- ✅ **Cost**: <£5 per request (infrastructure + LLM + observability)
- ✅ **Auditability**: 100% of decisions traceable to source documents

### Regulatory Metrics (UK August 2026 Readiness)
- ✅ **Identity-Based Accountability**: Every agent action tied to specific agent identity
- ✅ **Deterministic Guardrails**: All tool calls validated against JSON schema
- ✅ **Kill-Switch Capability**: Ability to pause/revoke tools in <5 seconds
- ✅ **Decision Logs**: Exportable audit trail for regulatory review
- ✅ **Data Lineage**: Tracking of all data sources used in RAG

---

## COMMUNICATION PROTOCOL (REFERENCE)

Every inter-agent message follows this immutable structure:

```json
{
  "message_id": "uuid",
  "timestamp": "2025-05-20T14:32:00Z",
  "from_agent": "domain_analyst",
  "to_agent": "orchestrator",
  "task_id": "task_uuid",
  "message_type": "task_complete|escalation|conflict|approval_request",
  "status": "in_progress|completed|failed|requires_human_input",
  "data": {
    "result": "Analysis summary...",
    "citations": [
      {"source": "document_id", "section": "s.23", "relevance": 0.92},
      {"source": "web_url", "date_retrieved": "2025-05-20", "relevance": 0.88}
    ],
    "confidence": 0.87,
    "rationale": "Reasoning chain that led to this output"
  },
  "metadata": {
    "context_tokens_used": 4200,
    "llm_model": "claude-sonnet-4-20250514",
    "duration_ms": 3400,
    "deterministic_checkpoint": "task_domain_analyst_contract_review_v2"
  },
  "escalation_flags": [],
  "signature": "base64_encoded_ed25519_signature"
}
```

---

## GETTING HELP

- **Architecture Questions**: Refer to ARCHITECTURE.md and DECISION_RECORDS.md
- **Sprint Tasks**: Check the active sprint guide (e.g., SPRINT_2_ORCHESTRATION.md)
- **Agent Behavior**: Refer to AGENTS.md (the "Employee Handbook")
- **Security Concerns**: Check SECURITY_ARCHITECTURE.md and coordinate with Security Engineer
- **Regulatory/Compliance**: Refer to docs/REGULATORY_FRAMEWORK.md and SPRINT_7_COMPLIANCE_LAYER.md

---

## LICENSE & GOVERNANCE

**Confidential. For internal development only.**

This project is proprietary software. All code, designs, and documentation are confidential. Do not share outside the development team without explicit approval.

---

## VERSION HISTORY

| Date | Version | Status | Notes |
|------|---------|--------|-------|
| 2025-05-20 | 1.0 | ACTIVE | Initial TDD + Sprint plan. Ready for development. |

---

**Last Updated**: 2025-05-20  
**Next Review**: End of Sprint 1 (2025-06-03)  
**Owner**: Architecture Team

