# SETUP GITHUB + CURSOR AUTOMATION GUIDE

## STEP 1: CLONE YOUR REPO & ADD PROJECT FILES

```bash
# Clone your repo
git clone https://github.com/serverax/aia.git
cd aia

# Initialize with all documentation (copy-paste these commands one by one)
```

## STEP 2: CREATE ALL FILES FROM THIS GUIDE

I'll provide the exact content for each file below. Copy-paste into your editor.

---

# FILES TO CREATE IN YOUR REPO

## File 1: .gitignore
```
# Python
__pycache__/
*.py[cod]
*.so
.Python
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp

# Environment
.env
.env.local

# Secrets
*.key
*.pem
infrastructure/cosign/cosign.key

# Terraform
infrastructure/terraform/.terraform/
*.tfstate

# Node
node_modules/
dist/
build/

# OS
.DS_Store
Thumbs.db
```

## File 2: .cursor/cursor_sprint_guide.md
```markdown
# Cursor Sprint Guide - Synthetic Enterprise

You are implementing Synthetic Enterprise, a multi-agent AI orchestration system.

## CRITICAL CONSTRAINTS (ALWAYS FOLLOW)
- Temperature=0 for all LLM calls (determinism required)
- All agent communication via Redis (async, no direct calls)
- Every output must cite sources (no hallucination)
- Compliance Officer has veto power
- Humans make final high-stakes decisions
- No cross-tenant data leakage

## SPRINT WORKFLOW

### BEFORE EACH SPRINT
1. Read the sprint document: SPRINT_X_*.md
2. Review AGENTS.md for agent constraints
3. Review ARCHITECTURE.md for communication patterns

### DURING EACH SPRINT
1. For each task in the sprint:
   a. Ask Cursor: "I'm starting [TASK NAME] from [SPRINT NUMBER]. Guide me through the implementation."
   b. Cursor will reference the sprint document and provide step-by-step guidance
   c. Follow the guidance and implement the code
   d. Run tests (pytest for Python, npm test for Node)
   
2. If you get stuck:
   a. Ask: "Check AGENTS.md - does [agent name] have permission to do [action]?"
   b. Ask: "Verify this code follows the message protocol from ARCHITECTURE.md"
   c. Ask: "Is this deterministic? Check for temperature, randomness, or non-deterministic operations"

### AFTER EACH TASK
1. Commit to Git:
   ```bash
   git add .
   git commit -m "Task X.Y: [Task Name] - implementation complete"
   git push origin main
   ```

2. Mark task complete in SPRINT_TRACKING.md

3. Move to next task

## SPRINT SCHEDULE

- **Sprint 1 (Weeks 1-2)**: Infrastructure & Echo Agent
- **Sprint 2 (Weeks 3-4)**: Orchestrator & Routing
- **Sprint 3 (Weeks 5-7)**: RAG & Knowledge Integration
- **Sprint 4 (Weeks 8-9)**: Frontend & Approval Gates
- **Sprint 5 (Weeks 10-11)**: Editor & Document Finalization
- **Sprint 6 (Weeks 12-13)**: Wasm Security Layer
- **Sprint 7 (Weeks 14-15)**: Compliance Controls
- **Sprint 8 (Week 16)**: Production Hardening

## CURSOR COMMANDS FOR EACH SPRINT

See below for specific Cursor prompts.
```

## File 3: SPRINT_TRACKING.md
```markdown
# Sprint Tracking

## Sprint 1: Infrastructure (Weeks 1-2)
- [ ] Task 1.1: Provision bare-metal infrastructure
- [ ] Task 1.2: Install Talos Linux & K3s
- [ ] Task 1.3: Deploy Redis
- [ ] Task 1.4: Deploy PostgreSQL
- [ ] Task 1.5: Set up OpenTelemetry
- [ ] Task 1.6: Build Echo Agent
- [ ] Task 1.7: Documentation & Handoff

**Status**: Not Started
**Completion**: 0%

---

## Sprint 2: Orchestration (Weeks 3-4)
- [ ] Task 2.1: Implement Orchestrator Agent
- [ ] Task 2.2: Build Compliance Officer Agent
- [ ] Task 2.3: Implement Conflict Resolution
- [ ] Task 2.4: Integration Testing
- [ ] Task 2.5: Documentation

**Status**: Not Started
**Completion**: 0%

---

## Sprint 3: RAG (Weeks 5-7)
- [ ] Task 3.1: Qdrant Deployment
- [ ] Task 3.2: Milvus Deployment
- [ ] Task 3.3: Tool Integration
- [ ] Task 3.4: Deterministic Evaluation

**Status**: Not Started
**Completion**: 0%

---

## Sprint 4: Frontend (Weeks 8-9)
- [ ] Task 4.1: WebSocket Server
- [ ] Task 4.2: React Dashboard
- [ ] Task 4.3: Approval Gate UI

**Status**: Not Started
**Completion**: 0%

---

## Sprint 5: Editor (Weeks 10-11)
- [ ] Task 5.1: Editor Agent
- [ ] Task 5.2: Template System

**Status**: Not Started
**Completion**: 0%

---

## Sprint 6: Wasm Security (Weeks 12-13)
- [ ] Task 6.1: WasmEdge Integration
- [ ] Task 6.2: Tool Sandboxing
- [ ] Task 6.3: Artifact Signing

**Status**: Not Started
**Completion**: 0%

---

## Sprint 7: Compliance (Weeks 14-15)
- [ ] Task 7.1: Kill-Switch API
- [ ] Task 7.2: Compliance Middleware

**Status**: Not Started
**Completion**: 0%

---

## Sprint 8: Hardening (Week 16)
- [ ] Task 8.1: Load Testing
- [ ] Task 8.2: Security Audit
- [ ] Task 8.3: SLA Definition

**Status**: Not Started
**Completion**: 0%
```

## File 4: .cursor/rules.md
```markdown
# Cursor Rules - Synthetic Enterprise

## INVIOLABLE CONSTRAINTS

### Architecture
- NEVER call agent functions directly
- ALL communication via Redis (async)
- Infrastructure ≠ Orchestration ≠ Communication

### Agents (See AGENTS.md)
- Orchestrator: Decompose & route only
- Compliance Officer: Has VETO power
- Analyst: MUST cite all sources
- Editor: Format only, don't rewrite

### LLM
- ALWAYS temperature=0
- NEVER use random operations
- EVERY output must cite sources

### Data Security
- NO cross-client data access
- NO plaintext secrets
- NO agent veto bypassing

## RED FLAGS
🚫 Adding randomness
🚫 Direct agent calls
🚫 Plaintext secrets
🚫 Autonomous decisions
🚫 Cross-tenant data
🚫 Veto bypassing
🚫 Temperature > 0
🚫 Uncited claims

When you see these, STOP and ask.
```

## File 5: requirements.txt
```
langgraph==0.1.0
langchain==0.1.0
langchain-anthropic==0.1.0
pydantic==2.5.0
redis==5.0.0
psycopg2-binary==2.9.9
qdrant-client==2.7.0
pymilvus==2.3.0
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-exporter-jaeger==1.21.0
pytest==7.4.3
pytest-asyncio==0.23.1
pytest-cov==4.1.0
python-dotenv==1.0.0
httpx==0.25.2
```

---

# NOW: PUSH TO GITHUB

```bash
cd /path/to/aia

# Stage all files
git add .

# Create initial commit
git commit -m "Initial: Synthetic Enterprise - Complete technical specification + sprint automation"

# Push to GitHub
git push origin main

# Verify on GitHub
echo "✅ Check https://github.com/serverax/aia"
```

---

# CURSOR SPRINT AUTOMATION

## HOW TO USE WITH CURSOR

1. **Open your repo in Cursor**:
   ```bash
   cursor /path/to/aia
   ```

2. **For each sprint, use these prompts**:

---

## SPRINT 1 PROMPTS

### Task 1.1: Infrastructure Setup
**Cursor Prompt**:
```
I'm starting SPRINT_1_INFRASTRUCTURE Task 1.1: Provision bare-metal infrastructure.

Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.1

Guide me through:
1. Creating Terraform code for Hetzner
2. Provisioning 3 servers
3. Verifying SSH access

Show me the terraform/hetzner.tf file content.
```

### Task 1.2: K3s Installation
**Cursor Prompt**:
```
I'm on SPRINT_1_INFRASTRUCTURE Task 1.2: Install Talos Linux & K3s

Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.2

Create:
1. Talos configuration patches
2. Installation scripts
3. kubeconfig retrieval commands

Show exact commands I should run.
```

### Task 1.3: Redis Setup
**Cursor Prompt**:
```
SPRINT_1_INFRASTRUCTURE Task 1.3: Deploy Redis

Create a Helm values.yaml file for Redis with:
- Streams enabled
- Persistence enabled (AOF)
- Authentication enabled
- Metrics enabled

Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.3
```

### Task 1.4: PostgreSQL Setup
**Cursor Prompt**:
```
SPRINT_1_INFRASTRUCTURE Task 1.4: Deploy PostgreSQL

Create:
1. Helm values.yaml for PostgreSQL
2. audit_log_schema.sql with immutability constraints
3. Backup configuration

Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.4
```

### Task 1.5: OpenTelemetry Setup
**Cursor Prompt**:
```
SPRINT_1_INFRASTRUCTURE Task 1.5: OpenTelemetry

Create:
1. Jaeger Helm deployment
2. OpenTelemetry collector config
3. Python otel_helper.py

Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.5
```

### Task 1.6: Echo Agent
**Cursor Prompt**:
```
SPRINT_1_INFRASTRUCTURE Task 1.6: Echo Agent implementation

Create services/echo-agent/:
1. main.py - Listen to Redis, echo back messages
2. Dockerfile
3. requirements.txt
4. Unit tests (test_agent.py)
5. K3s deployment YAML

Requirements:
- temperature=0
- Deterministic checkpointing
- Message signing

Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.6 + AGENTS.md
```

### Task 1.7: Integration Tests
**Cursor Prompt**:
```
SPRINT_1_INFRASTRUCTURE Task 1.7: Integration tests

Create infrastructure/tests/integration_test_echo_agent.sh:
1. Deploy Echo Agent
2. Send test message to Redis
3. Verify response
4. Kill pod
5. Verify recovery from checkpoint

Show exact bash commands.
```

---

## SPRINT 2 PROMPTS

### Task 2.1: Orchestrator Agent
**Cursor Prompt**:
```
SPRINT_2_ORCHESTRATION Task 2.1: Orchestrator Agent

Create services/orchestrator-agent/:
1. state.py - State schema (intent, tasks, graph)
2. nodes.py - LangGraph nodes (intent_parser, decomposer)
3. router.py - Task routing logic
4. graph.py - Full LangGraph workflow
5. Unit tests

Requirements from AGENTS.md:
- Parses user intent
- Decomposes into atomic tasks
- Routes to Analyst/Compliance/Editor
- No heavy reasoning
- Respects constraints

Reference: SPRINT_2_ORCHESTRATION.md Task 2.1 + AGENTS.md
```

### Task 2.2: Compliance Officer Agent
**Cursor Prompt**:
```
SPRINT_2_ORCHESTRATION Task 2.2: Compliance Officer

Create services/compliance-agent/:
1. main.py - Listen for tasks
2. compliance_checker.py - Verify UK regulations
3. Unit tests

Requirements from AGENTS.md:
- Has VETO power
- Must cite decisions
- Never approve if unsure

Reference: SPRINT_2_ORCHESTRATION.md Task 2.2 + AGENTS.md
```

### Task 2.3: Conflict Resolution
**Cursor Prompt**:
```
SPRINT_2_ORCHESTRATION Task 2.3: Conflict resolution

Create services/orchestrator-agent/conflict_resolver.py:
1. detect_conflict() - Find contradictory outputs
2. run_debate_protocol() - Ask agents to defend positions
3. escalate_to_human() - Escalate if unresolved

Requirements:
- Detect Analyst vs Compliance disagreements
- Run debate with rationale exchange
- Escalate after 2 rounds if unresolved

Reference: SPRINT_2_ORCHESTRATION.md Task 2.3
```

### Task 2.4: Integration Test
**Cursor Prompt**:
```
SPRINT_2_ORCHESTRATION Task 2.4: End-to-end workflow test

Create infrastructure/tests/sprint2_orchestration_test.sh:
1. Deploy all agents (Orchestrator, Compliance, Analyst)
2. Send complex request: "Draft a settlement agreement"
3. Verify task decomposition
4. Verify task routing
5. Verify conflict detection

Show exact bash test script.
```

---

## SPRINT 3 PROMPTS

### Task 3.1: Qdrant Setup
**Cursor Prompt**:
```
SPRINT_3 Task 3.1: Qdrant for Compliance Officer

Create:
1. Helm values for Qdrant
2. qdrant_indexer.py - Index UK legislation
3. Test that legislation search works

Requirements:
- Vector size: 1536
- Collection: uk_compliance
- Metadata: regulation, section, jurisdiction, source

Reference: SPRINT_3_THROUGH_8.md Section 3.1
```

### Task 3.2: Milvus Setup
**Cursor Prompt**:
```
SPRINT_3 Task 3.2: Milvus for Analyst Agent

Create:
1. Helm values for Milvus
2. milvus_manager.py - Client partitioning
3. Test client isolation

Requirements:
- Client partitioning (client_a vs client_b)
- Isolation verification
- Hybrid search (semantic + BM25)

Reference: SPRINT_3_THROUGH_8.md Section 3.2
```

### Task 3.3: Tool Integration
**Cursor Prompt**:
```
SPRINT_3 Task 3.3: Tools for agents

Create libs/communication/tools.py:
1. web_search() - DuckDuckGo
2. fetch_document() - Retrieve from Milvus
3. lookup_cvss_score() - Threat intelligence

Requirements:
- All tools must be Wasm-compatible (later)
- All tools must return structured JSON
- Tools must include error handling

Reference: SPRINT_3_THROUGH_8.md Section 3.3
```

### Task 3.4: Determinism Tests
**Cursor Prompt**:
```
SPRINT_3 Task 3.4: Determinism evaluation

Create libs/evaluation/determinism_evals.py:
1. Run same request 5 times
2. Verify identical output each time
3. Report non-determinism if found

Requirements:
- Test all agents
- temperature=0 verification
- Benchmark dataset of 10 test requests

Reference: SPRINT_3_THROUGH_8.md Section 3.4
```

---

## SPRINT 4 PROMPTS

### Task 4.1: WebSocket Server
**Cursor Prompt**:
```
SPRINT_4 Task 4.1: Real-time WebSocket updates

Create apps/api-gateway/websocket_server.py:
1. FastAPI WebSocket endpoint
2. Broadcast agent status updates
3. Stream task progress to UI

Requirements:
- Endpoint: /ws/{project_id}
- Stream: agent status, task progress, escalations
- Channel: ui:updates:{project_id}

Reference: SPRINT_3_THROUGH_8.md Section "SPRINT 4"
```

### Task 4.2: React Dashboard
**Cursor Prompt**:
```
SPRINT_4 Task 4.2: Agent Monitor Component

Create apps/web-dashboard/src/components/AgentMonitor.tsx:
1. React component with WebSocket hook
2. Display real-time agent status
3. Show task graph
4. Render agent cards

Requirements:
- Use react-use-websocket
- Update state on message
- Show agent status (idle, working, error)

Reference: SPRINT_3_THROUGH_8.md Section "SPRINT 4"
```

### Task 4.3: Approval Gate UI
**Cursor Prompt**:
```
SPRINT_4 Task 4.3: Approval Gate Component

Create apps/web-dashboard/src/components/ApprovalGate.tsx:
1. Display escalation (red border)
2. Two-column debate view
3. Action buttons (Approve, Revise, Reject)
4. Send decision to backend

Requirements:
- Show agent_a vs agent_b positions
- POST to /api/escalations/{id}/approve
- Log decision

Reference: SPRINT_3_THROUGH_8.md Section "SPRINT 4"
```

---

## SPRINT 5-8 PROMPTS

[Similar structure for remaining sprints]

---

# QUICK START COMMAND

Copy-paste this to get started immediately:

```bash
# 1. Clone your repo
git clone https://github.com/serverax/aia.git
cd aia

# 2. Create initial structure
mkdir -p {services/{orchestrator-agent,compliance-agent,analyst-agent,editor-agent},\
          apps/{web-dashboard,api-gateway},\
          libs/{communication,infrastructure,evaluation,tracing,security},\
          infrastructure/{terraform,helm-charts,sql,ci},\
          tests/{unit,integration,evals},\
          docs,sprints,scripts,config,.github/workflows,.cursor}

# 3. Copy all the files from above into appropriate locations

# 4. Initialize Git
git add .
git commit -m "Initial: Synthetic Enterprise project"
git push origin main

# 5. Open in Cursor
cursor .

# 6. Start Sprint 1
# Read: SPRINT_1_INFRASTRUCTURE.md
# Ask Cursor: "I'm starting SPRINT_1 Task 1.1. Guide me."
```

---

# THAT'S IT!

From there, just follow the Cursor prompts for each sprint. Each prompt will guide you through the exact implementation.

**Estimated time**: 16 weeks (2 weeks per sprint)

**Total commits**: ~60 (one per task)

**Final result**: Production-ready Synthetic Enterprise system 🎉
