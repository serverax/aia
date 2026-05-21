# 🚀 START NOW - EXACT COMMANDS

## STEP 1: Clone Your Repo (Copy-Paste This)

**Windows (PowerShell as Admin)**:
```powershell
cd F:\
git clone https://github.com/serverax/aia.git
cd aia
```

**macOS/Linux**:
```bash
cd ~
git clone https://github.com/serverax/aia.git
cd aia
```

---

## STEP 2: Create Project Structure

**Windows**:
```powershell
$dirs = @(
    "services/orchestrator-agent", "services/compliance-agent", "services/analyst-agent", "services/editor-agent",
    "apps/web-dashboard", "apps/api-gateway",
    "libs/communication", "libs/infrastructure", "libs/evaluation", "libs/tracing", "libs/security",
    "infrastructure/terraform", "infrastructure/helm-charts", "infrastructure/sql", "infrastructure/ci",
    "tests/unit", "tests/integration", "tests/evals",
    "docs", "sprints", "scripts", "config", ".github/workflows", ".cursor"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

echo "✅ Directories created"
```

**macOS/Linux**:
```bash
mkdir -p services/{orchestrator-agent,compliance-agent,analyst-agent,editor-agent}
mkdir -p apps/{web-dashboard,api-gateway}
mkdir -p libs/{communication,infrastructure,evaluation,tracing,security}
mkdir -p infrastructure/{terraform,helm-charts,sql,ci}
mkdir -p tests/{unit,integration,evals}
mkdir -p docs sprints scripts config .github/workflows .cursor
echo "✅ Directories created"
```

---

## STEP 3: Create Essential Files

### Create .gitignore
```bash
cat > .gitignore << 'GITIGNORE'
__pycache__/
*.py[cod]
.Python
venv/
ENV/
.venv
.vscode/
.idea/
*.swp
.env
.env.local
*.key
*.pem
infrastructure/terraform/.terraform/
*.tfstate
node_modules/
dist/
build/
.DS_Store
Thumbs.db
GITIGNORE
```

### Create requirements.txt
```bash
cat > requirements.txt << 'REQUIREMENTS'
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
REQUIREMENTS
```

---

## STEP 4: Copy Documentation Files

**Download these files from** `/mnt/user-data/outputs/` **and copy:**

```
Root directory (F:\aia\):
- 00_START_HERE.md
- README.md
- ARCHITECTURE.md
- AGENTS.md
- DEVELOPER_QUICK_START.md
- IMPLEMENTATION_SUMMARY.md
- PROJECT_STRUCTURE.md
- SPRINT_TRACKING.md (optional, create manually)

docs/ subdirectory:
- SECURITY_ARCHITECTURE.md
- REGULATORY_FRAMEWORK.md

sprints/ subdirectory:
- SPRINT_1_INFRASTRUCTURE.md
- SPRINT_2_ORCHESTRATION.md
- SPRINT_3_THROUGH_8.md

.cursor/ subdirectory:
- Create .cursor/rules.md (see below)
```

### Create .cursor/rules.md (Paste This)
```bash
cat > .cursor/rules.md << 'RULES'
# Cursor Rules - Synthetic Enterprise

## CRITICAL CONSTRAINTS

### Architecture
- NEVER call agent functions directly - use Redis message bus
- ALL communication is async via Redis Streams/Pub/Sub
- Infrastructure layer ≠ Orchestration layer ≠ Communication layer

### Agents (See AGENTS.md)
- **Orchestrator**: Decompose & route ONLY - don't do reasoning
- **Compliance Officer**: Has VETO power - can block outputs
- **Analyst**: MUST cite all sources - no hallucination
- **Editor**: Format ONLY - never rewrite content meaning

### LLM Calls
- ALWAYS set temperature=0 (determinism required for audit)
- NEVER use random() or non-deterministic operations
- EVERY output must include citations with sources

### Data Security
- NO cross-client data access (K3s namespaces + Milvus partitions)
- NO plaintext secrets in code
- NO bypassing Compliance Officer veto

## RED FLAGS - STOP AND ASK FIRST
🚫 Adding randomness to logic
🚫 Direct function calls between agents
🚫 Plaintext secrets
🚫 Agent making autonomous decisions
🚫 Cross-tenant data access
🚫 Bypassing Compliance veto
🚫 Temperature > 0 for LLM
🚫 Claims without citations

When you see these patterns, STOP and ask the architect.
RULES
```

---

## STEP 5: Push to GitHub

```bash
# Stage all files
git add .

# Create initial commit
git commit -m "Initial: Synthetic Enterprise - Complete TDD + 8-sprint roadmap + automation"

# Push to main branch
git push -u origin main

# Verify
echo "✅ Check https://github.com/serverax/aia"
```

---

## STEP 6: Open in Cursor

```bash
# Open your repo in Cursor
cursor .
```

Or in Cursor:
- File → Open Folder
- Select your aia directory
- Cursor will auto-detect .cursor/rules.md

---

## STEP 7: START SPRINT 1 WITH CURSOR

**Copy-paste this prompt into Cursor's chat:**

```
I'm starting SPRINT_1_INFRASTRUCTURE Task 1.1: Provision bare-metal infrastructure.

Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.1

Create:
1. infrastructure/terraform/hetzner.tf - Terraform code for Hetzner servers
2. infrastructure/inventory.md - Document server IPs

Requirements:
- 3 servers: 64GB RAM, 8 cores, NVMe SSD
- Network: Hetzner private network with VLAN
- Location: EU
- Output: documented IPs in inventory.md

Show me the exact terraform code I should use.
```

Cursor will guide you through the implementation.

---

## ✅ CHECKLIST: YOU'RE READY

- [ ] Cloned repo from GitHub
- [ ] Created directory structure
- [ ] Created .gitignore, requirements.txt, .cursor/rules.md
- [ ] Downloaded and copied all .md documentation files
- [ ] Pushed to GitHub
- [ ] Opened in Cursor
- [ ] Ready to start Sprint 1

---

## 📊 WHAT HAPPENS NEXT

### Week 1-2 (Sprint 1)
- Task 1.1: Provision 3 bare-metal servers
- Task 1.2: Install Talos Linux + K3s
- Task 1.3: Deploy Redis
- Task 1.4: Deploy PostgreSQL
- Task 1.5: Deploy OpenTelemetry
- Task 1.6: Build Echo Agent
- Task 1.7: Integration tests

**Deliverable**: K3s cluster running, message bus working, Echo Agent proves system is sound

### Week 3-4 (Sprint 2)
- Task 2.1: Orchestrator Agent (LangGraph)
- Task 2.2: Compliance Officer Agent
- Task 2.3: Conflict resolution
- Task 2.4: Integration testing

**Deliverable**: Multi-agent routing working

### Week 5-16 (Sprints 3-8)
- RAG pipelines (Qdrant + Milvus)
- Real-time UI (WebSocket + React)
- Document generation
- Wasm security layer
- Compliance controls
- Production hardening

**Final Deliverable**: Production-ready Synthetic Enterprise system 🚀

---

## 🎯 CURSOR WORKFLOW

For each task:

1. **Read the sprint document** (e.g., SPRINT_1_INFRASTRUCTURE.md)
2. **Copy the task prompt** from CURSOR_MASTER_AUTOMATION.md
3. **Paste into Cursor** chat
4. **Follow Cursor's guidance**
5. **Implement the code**
6. **Run tests**
7. **Commit to Git**:
   ```bash
   git add .
   git commit -m "Sprint 1 Task 1.1: Terraform infrastructure setup"
   git push origin main
   ```
8. **Move to next task**

---

## ⚡ FASTEST POSSIBLE START

**Right now, copy-paste these 3 commands**:

```bash
cd F:\aia
git init
git remote add origin https://github.com/serverax/aia.git
```

Then:

```bash
# Create directories
mkdir -p services/{orchestrator-agent,compliance-agent,analyst-agent,editor-agent} apps/{web-dashboard,api-gateway} libs/{communication,infrastructure,evaluation,tracing,security} infrastructure/{terraform,helm-charts,sql,ci} tests/{unit,integration,evals} docs sprints scripts config .github/workflows .cursor

# Push to GitHub
git add .
git commit -m "Initial: Synthetic Enterprise"
git push -u origin main

# Open in Cursor
cursor .
```

That's it! You're ready to start Sprint 1.

---

## 📝 REFERENCE

- **Sprint Prompts**: See CURSOR_MASTER_AUTOMATION.md
- **Architecture**: See ARCHITECTURE.md
- **Agent Constraints**: See AGENTS.md
- **Current Sprint Tasks**: See sprints/SPRINT_*.md

---

## 🚀 YOU'RE READY!

Download the .md files from `/mnt/user-data/outputs/`, copy them to your aia directory, then start with the commands above.

**Estimated time to first working code**: 30 minutes
**Estimated time to production-ready system**: 16 weeks

Let's build Synthetic Enterprise! 🎉
