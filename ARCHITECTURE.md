# ARCHITECTURE.md: Synthetic Enterprise Design Patterns

## EXECUTIVE SUMMARY

We are building a **decoupled, event-driven, hierarchical multi-agent system**. This document defines the core architectural patterns that prevent the system from becoming a monolithic bottleneck.

### Core Design Principle
**Separation of Concerns**:
- **Infrastructure Layer**: K3s/Talos manages WHERE code runs (containers, networking, storage).
- **Orchestration Layer**: LangGraph manages WHAT agents do (task decomposition, routing, conflict resolution).
- **Communication Layer**: Redis event bus enables async, decoupled agent-to-agent messaging.

This separation ensures that we can scale agents independently, update orchestration logic without touching infrastructure, and maintain a clear audit trail.

---

## PART 1: THE DECOUPLED ARCHITECTURE PATTERN

### Why Decoupling Matters

**Problem**: A monolithic "Master Algorithm" that controls all agent behavior becomes a single point of failure. If it crashes, the entire platform stops.

**Solution**: Three independent layers, connected by well-defined interfaces:

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                       │
│          (React Dashboard + WebSocket channel)           │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────────────┐  ┌──▼────────────────────────┐
│  ORCHESTRATION LAYER     │  │  COMMUNICATION LAYER      │
│  (LangGraph)             │  │  (Redis Event Bus)        │
│  ─────────────────────── │  │  ──────────────────────── │
│  • Task decomposition    │  │  • Async messaging        │
│  • Agent routing         │  │  • Pub/Sub channels       │
│  • State management      │  │  • Message persistence    │
│  • Conflict resolution   │  │  • Dead-letter handling   │
└───────┬──────────────────┘  └──┬────────────────────────┘
        │                         │
        └────────────┬────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼────────────┐ ┌▼──────────────┐ ┌▼──────────────┐
│  COMPLIANCE    │ │   DOMAIN      │ │   EDITOR/     │
│  AGENT POD     │ │   ANALYST POD │ │   FINALIZER   │
│                │ │               │ │   POD         │
│ (Kubernetes)   │ │ (Kubernetes)  │ │ (Kubernetes)  │
└────────────────┘ └───────────────┘ └───────────────┘
        │                │                │
        └────────────────┼────────────────┘
                     │
        ┌────────────▼────────────┐
        │  INFRASTRUCTURE LAYER   │
        │  (Talos Linux + K3s)    │
        │  ─────────────────────  │
        │  • Auto-scaling         │
        │  • Load balancing       │
        │  • Resource management  │
        │  • Networking & security│
        └────────────────────────┘
```

### Layer Responsibilities

#### Infrastructure Layer (Talos Linux + K3s)
- **Does NOT know**: What agents do, how they reason, what data they process.
- **Does know**: CPU/memory allocation, pod scheduling, networking policies, storage replication.
- **Tech**: Kubernetes resources (Deployments, Services, PersistentVolumes), NetworkPolicies, RBAC.
- **Example decision**: "The Analyst Pod is using 85% RAM. Scale up to 3 replicas."

#### Orchestration Layer (LangGraph)
- **Does NOT know**: Where code runs, how messages are persisted, what hardware exists.
- **Does know**: Task decomposition, agent routing, state transitions, conflict resolution.
- **Tech**: LangGraph state graphs, Python async logic, deterministic checkpoints.
- **Example decision**: "The Analyst returned suspicious results. Escalate to Compliance Officer for review."

#### Communication Layer (Redis)
- **Does NOT know**: What messages mean, how agents interpret data, task logic.
- **Does know**: Publishing, subscribing, persistence, ordering guarantees.
- **Tech**: Redis Streams, Pub/Sub, transactions.
- **Example decision**: "Message from Analyst arrived. Persist to stream; notify subscribers."

### The Consequence: Modularity

Because these layers are decoupled:

1. **Update Orchestration**: Change agent prompts, routing logic, state machines → **no infrastructure restart needed**.
2. **Scale Infrastructure**: Add K3s nodes, expand storage → **agents keep running, no downtime**.
3. **Debug Issues**: Trace a user request from frontend → orchestrator → agents → infrastructure → database. Each layer's failures are isolated.

---

## PART 2: EVENT-DRIVEN COMMUNICATION PROTOCOL

### Why Event-Driven?

In a synchronous system:
- Agent A calls Agent B's function.
- Agent B processes.
- Agent A waits.
- If Agent B is slow or crashes, Agent A blocks.

In an event-driven system:
- Agent A publishes an event: `"DraftReviewRequested"`.
- Agent A continues its own work.
- Agent B subscribes to `"DraftReviewRequested"` and processes when ready.
- No blocking. If Agent B crashes, the message persists in Redis.

### Message Structure

Every inter-agent message is a deterministic JSON object:

```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-05-20T14:32:00Z",
  "task_id": "task_987654",
  "project_id": "client_acme_2025_q2",
  
  "from_agent": "domain_analyst",
  "to_agent": "compliance_officer",
  "message_type": "task_complete",
  "priority": "high",
  
  "status": "completed",
  "data": {
    "result": {
      "analysis_summary": "Contract contains IP indemnification clause...",
      "key_findings": [
        {
          "finding": "Clause X may violate unfair terms act",
          "evidence": "Case law citation: Unfair Contract Terms Act 1977, s.3",
          "source_document_id": "contract_version_3",
          "confidence": 0.92
        }
      ]
    },
    "citations": [
      {
        "source_type": "document",
        "document_id": "contract_version_3",
        "section": "Article 5.2",
        "text_excerpt": "Vendor shall indemnify Client against all claims...",
        "relevance_score": 0.95
      },
      {
        "source_type": "case_law",
        "case_name": "Unfair Contract Terms Act 1977",
        "jurisdiction": "UK",
        "retrieved_from": "qdrant_compliance_db",
        "retrieved_at": "2025-05-20T14:30:00Z"
      }
    ],
    "confidence": 0.87,
    "rationale": "Analysis chain: (1) Parsed contract structure. (2) Identified indemnification clauses. (3) Cross-referenced against UK UCTA 1977 guidance. (4) Found potential violation in case law precedent."
  },
  
  "metadata": {
    "context_tokens_used": 4200,
    "llm_model": "claude-sonnet-4-20250514",
    "duration_ms": 3847,
    "deterministic_checkpoint": "task_987654_analyst_review_v2",
    "tool_calls": [
      {
        "tool": "qdrant_search",
        "query": "unfair contract terms indemnification",
        "results_count": 5
      }
    ]
  },
  
  "escalation_flags": [
    {
      "type": "regulatory_risk",
      "severity": "high",
      "description": "Potential UCTA 1977 violation detected",
      "suggested_action": "Escalate to Compliance Officer"
    }
  ],
  
  "signature": "base64_encoded_ed25519_signature_of_entire_payload"
}
```

### Message Type Definitions

| Message Type | From | To | Meaning |
|--------------|------|----|---------| 
| `task_assign` | Orchestrator | Agent | "Here's a task. Get started." |
| `task_progress` | Agent | Orchestrator | "I'm working on this. Current progress: 60%." |
| `task_complete` | Agent | Orchestrator | "I finished. Here are my results." |
| `task_failed` | Agent | Orchestrator | "I couldn't complete this. Reason: [...]" |
| `escalation` | Agent | Orchestrator | "I found a problem. Human input needed." |
| `conflict` | Agent | Orchestrator | "I disagree with another agent. Let's debate." |
| `approval_request` | Orchestrator | User | "Critical decision pending. Click approve or reject." |
| `approval_response` | User | Orchestrator | "I approve this action." or "I reject it. Revise." |

### Redis Implementation

**Channels** (for real-time events):
```
agent:{agent_name}:tasks          # Agent listens for new tasks
agent:{agent_name}:commands       # System sends real-time commands (pause, stop, etc.)
orchestrator:status               # Agents broadcast status updates
ui:updates                        # Frontend listens for UI updates
```

**Streams** (for persistent, ordered messaging):
```
task_queue:{project_id}           # Ordered queue of tasks for a project
audit_log:{project_id}            # Immutable record of all actions
```

---

## PART 3: THE AGENT TAXONOMY (ROLES & RESPONSIBILITIES)

### Agent 1: ORCHESTRATOR (The Manager)

**Role**: Central coordinator. Decomposes user requests into tasks; routes to agents; manages state.

**Responsibilities**:
1. **Intent Parsing**: User input → structured task specification
   - Extract objective, scope, constraints, deadlines
   - Flag ambiguities; escalate to human if unclear
2. **Task Decomposition**: Break complex goals into atomic subtasks
   - Example: "Draft employment contract" → [research_precedents, draft_clauses, compliance_check, formatting]
3. **Agent Routing**: Assign each subtask to the right agent
   - Route research → Analyst
   - Route verification → Compliance Officer
   - Route formatting → Editor
4. **State Management**: Maintain the global task graph (Redis)
   - Track subtask status, dependencies, timeline
   - Detect cycles (e.g., Agent A waiting for Agent B, Agent B waiting for A)
5. **Conflict Resolution**: When agents disagree
   - Ask both agents for rationale
   - If unresolved, escalate to human
6. **Progress Reporting**: Real-time updates to UI

**Tools**:
- LLM: Claude Sonnet 4 (temperature=0)
- State store: Redis (fast transactions)
- Message broker: Redis Pub/Sub

**Key Constraint**: The Orchestrator must **not** execute complex reasoning. It must delegate. Its job is traffic control, not decision-making.

**Example Workflow**:
```
User: "Draft a settlement agreement for an employment dispute."

Orchestrator:
1. Parses intent: {objective: "settlement_agreement", domain: "employment_law", urgency: "high"}
2. Decomposes: [
     {task: "research_precedents", assigned_to: "analyst", priority: "high"},
     {task: "compliance_check", assigned_to: "compliance_officer", depends_on: ["research_precedents"]},
     {task: "draft_agreement", assigned_to: "analyst", depends_on: ["compliance_check"]},
     {task: "format_document", assigned_to: "editor", depends_on: ["draft_agreement"]}
   ]
3. Publishes task_assign messages to Redis
4. Waits for agents to complete
5. If Compliance Officer flags risks, escalates to human before proceeding
```

---

### Agent 2: COMPLIANCE OFFICER (The Gatekeeper)

**Role**: Regulatory guardian. Every output is screened against UK law before it leaves the system.

**Responsibilities**:
1. **Regulatory Screening**: Check outputs against:
   - UK legislation (Employment Rights Act, GDPR, etc.)
   - SRA principles (if legal)
   - Firm policies (version-controlled in Git)
   - Case law precedents
2. **Risk Flagging**: Identify legal landmines
   - "This clause may breach UCTA 1977"
   - "GDPR consent not documented for this data"
3. **Veto Authority**: Can block outputs that breach compliance
4. **Audit Trail**: Log every compliance decision with rationale

**Tools**:
- Vector DB: Qdrant (UK legislation + SRA guidance)
- LLM: Claude Sonnet 4
- Custom tools: `check_sra_principles()`, `flag_gdpr_risk()`, `validate_employment_clause()`

**Isolation**: The Compliance Officer has its own isolated Qdrant instance containing ONLY UK regulatory data. It cannot access client confidential data (that's in the Analyst's DB).

**Key Constraint**: The Compliance Officer must **never** approve something it doesn't understand. If a clause is ambiguous, it flags it as "amber" and requests human review.

**Example Interaction**:
```
Analyst completes: {
  "result": "Settlement agreement drafted. Offers £50,000 severance.",
  "citations": [...]
}

Compliance Officer receives this message. It:
1. Searches Qdrant for "severance_agreements_employment_law"
2. Cross-references against ACAS guidance
3. Returns: {
     "compliant": true,
     "risk_level": "green",
     "flags": [],
     "approval_status": "approved"
   }

If a red flag exists (e.g., "No confidentiality clause"):
   "flags": [{
     "type": "legal_risk",
     "severity": "high",
     "description": "Settlement should include confidentiality covenant",
     "cite": "ACAS Guidance on Confidentiality",
     "remediation": "Add clause: 'Employee agrees not to disclose terms of settlement...'"
   }],
   "approval_status": "rejected"
```

---

### Agent 3: DOMAIN ANALYST (The Researcher)

**Role**: Subject-matter expertise engine. Performs research, analysis, reasoning using RAG.

**Responsibilities**:
1. **Real-time Research**: Fetch current data via RAG + web search
   - Market trends, financial data, precedents, threat intelligence
2. **Complex Analysis**: Multi-step reasoning
   - Contract review, risk assessment, technical analysis
3. **Citation**: All claims must be sourced
4. **Confidence Scoring**: Explicitly state uncertainty

**Tools**:
- Vector DB: Milvus (client-specific data, industry precedents)
- Web search: DuckDuckGo API
- Document fetch: Retrieve from client vault
- Financial modeling: Isolated Python sandbox
- Threat intelligence: CVSS, NVD APIs (for cybersecurity tasks)

**Isolation**: The Analyst has access to the current client's partition in Milvus. It CANNOT see other clients' data (enforced by namespace + partition keys).

**Key Constraint**: The Analyst must cite everything. If it cannot find a source for a claim, it must say "I don't know" or "This is my inference, not fact."

---

### Agent 4: EDITOR/FINALIZER (The Polish Agent)

**Role**: Quality control and formatting. Converts agent outputs into production-ready documents.

**Responsibilities**:
1. **Formatting & Structure**: Convert outputs into professional documents
   - Legal memos (case analysis format)
   - Compliance reports (executive summary + detail)
   - Security assessments (CVSS-scored vulnerabilities)
2. **Tone Consistency**: Match client brand/style
3. **QA Checks**: Verify no typos, broken references, technical errors
4. **Generative UI**: Create interactive components (if applicable)

**Tools**:
- Pandoc (format conversion: Markdown → DOCX, HTML, PDF)
- Template library (Git-versioned)
- Grammarly API (spell/grammar check)
- Custom validation: `validate_references()` → ensures all citations are correct

---

## PART 4: STATE MANAGEMENT & PERSISTENCE

### State Store Architecture

**Redis** (for fast, transactional state):
```json
{
  "task_graph:{project_id}:{task_id}": {
    "id": "task_987654",
    "status": "in_progress",
    "assigned_to": "domain_analyst",
    "started_at": 1716250320,
    "subtasks": [
      {
        "id": "subtask_1",
        "status": "completed",
        "assigned_to": "analyst",
        "output": "Research findings...",
        "checkpoints": [
          {
            "agent": "analyst",
            "status": "completed",
            "output_hash": "abc123",
            "timestamp": 1716250380
          }
        ]
      }
    ]
  }
}
```

**PostgreSQL** (for immutable audit log):
```sql
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT NOW(),
  user_id UUID,
  project_id UUID,
  message_id UUID UNIQUE,
  from_agent VARCHAR,
  to_agent VARCHAR,
  task_id UUID,
  status VARCHAR,
  data JSONB,
  signature BYTEA,
  
  -- Indexing for fast queries
  CONSTRAINT idx_audit_project UNIQUE (project_id, created_at, message_id)
);
```

### Deterministic Checkpointing

After every agent completes a task, save:

```json
{
  "checkpoint_id": "task_987654_analyst_review_v2",
  "task_id": "task_987654",
  "agent": "domain_analyst",
  "status": "completed",
  "timestamp": "2025-05-20T14:30:00Z",
  "output": { /* full agent output */ },
  "state_hash": "abc123def456"  // Hash of entire task state
}
```

**Use Case**: If a pod crashes during "formatting", the system can resume from the last checkpoint without re-running "research" and "compliance_check".

---

## PART 5: OBSERVABILITY & TRACING

Every agent action is traced end-to-end using OpenTelemetry:

```
User Request (Span: root)
├─ Orchestrator.parse_intent (Span: parse)
├─ Orchestrator.decompose_tasks (Span: decompose)
├─ Route to Domain Analyst (Span: route_analyst)
│  ├─ Analyst.search_qdrant (Span: qdrant_search)
│  ├─ Analyst.web_search (Span: web_search)
│  ├─ Analyst.llm_reasoning (Span: llm_call)
│  └─ Analyst.emit_result (Span: emit)
├─ Route to Compliance Officer (Span: route_compliance)
│  ├─ Officer.search_qdrant (Span: qdrant_search)
│  ├─ Officer.check_regulations (Span: llm_call)
│  └─ Officer.emit_decision (Span: emit)
└─ Route to Editor (Span: route_editor)
   ├─ Editor.format_output (Span: format)
   └─ Editor.generate_document (Span: generate)
```

Each span captures:
- Duration (latency)
- Tool calls (which RAG searches, LLM models)
- Errors (if any)
- Token usage (for cost tracking)

---

## PART 6: FAILURE MODES & RECOVERY

### Single Agent Failure
- Agent Pod crashes → K3s restarts pod
- Agent resumes from last checkpoint (no re-work)
- Orchestrator detects timeout, escalates to human

### Message Broker Failure
- Redis restarts (persistence enabled)
- In-flight messages re-delivered
- No message loss (Redis Streams)

### LLM API Failure
- Fallback to Claude Opus 4 (via LiteLLM)
- Retry with exponential backoff
- If all retries fail, escalate to human

### Human Approval Timeout
- If human doesn't respond in 24 hours, escalate to manager
- Task enters "on hold" state (not deleted)

---

## SUMMARY: Design Principles

| Principle | Implementation |
|-----------|-----------------|
| **Decoupling** | Infrastructure, Orchestration, Communication as separate layers |
| **Event-Driven** | All agent communication via Redis; no direct function calls |
| **Deterministic** | LLM temperature=0; checkpoints enable replay |
| **Auditable** | Every decision logged; immutable audit trail |
| **Scalable** | Agents can be scaled independently (K3s replicas) |
| **Resilient** | Failure of one agent doesn't crash the system |
| **Observable** | OpenTelemetry tracing from request to completion |

---

**Next Document**: AGENTS.md (Agent roles, prompts, constraints)

