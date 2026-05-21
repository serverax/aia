# PUSH TO GITHUB + CURSOR MASTER COMMAND

## STEP 1: PUSH EVERYTHING TO GITHUB (One Command)

**Copy-paste ONE of these:**

### Windows PowerShell
```powershell
cd F:\aia; git init; git remote add origin https://github.com/serverax/aia.git; git add .; git commit -m "Synthetic Enterprise: Complete TDD + 8-sprint roadmap"; git push -u origin main
```

### macOS/Linux Bash
```bash
cd ~/aia && git init && git remote add origin https://github.com/serverax/aia.git && git add . && git commit -m "Synthetic Enterprise: Complete TDD + 8-sprint roadmap" && git push -u origin main
```

**Result**: Everything pushed to https://github.com/serverax/aia ✅

---

## STEP 2: CURSOR MASTER COMMAND FOR ALL SPRINTS

**Run this in your terminal:**

```bash
cursor /path/to/aia
```

**Then use THIS prompt in Cursor chat to orchestrate all 8 sprints:**

---

## 🎯 CURSOR MASTER PROMPT (Copy-Paste Into Cursor)

```
# SYNTHETIC ENTERPRISE - 8-SPRINT ORCHESTRATION

You are my AI pair programmer for implementing Synthetic Enterprise across all 8 sprints.

CRITICAL RULES (ALWAYS FOLLOW):
1. temperature=0 for all LLM calls (determinism required)
2. All agent communication via Redis (async, no direct calls)
3. Every output must cite sources (no hallucination)
4. Compliance Officer has absolute VETO power
5. All code must be Wasm-compatible (later)

SPRINT WORKFLOW:
For each sprint:
1. Read the sprint document (SPRINT_X_*.md)
2. For each task, I'll ask you: "Guide me through [TASK NAME]"
3. You provide step-by-step implementation guidance
4. I implement the code, run tests, commit to Git
5. We move to next task

YOUR ROLE:
- Guide implementation (don't write complete code unless I ask)
- Verify constraints are met
- Check architecture compliance
- Ensure tests pass before moving forward

AVAILABLE RESOURCES:
- ARCHITECTURE.md - System design
- AGENTS.md - Agent constraints & rules
- SECURITY_ARCHITECTURE.md - Zero-Trust design
- REGULATORY_FRAMEWORK.md - UK compliance
- SPRINT_1_INFRASTRUCTURE.md - Tasks 1.1-1.7
- SPRINT_2_ORCHESTRATION.md - Tasks 2.1-2.4
- SPRINT_3_THROUGH_8.md - Tasks 3.1-8.3

I'm ready to start SPRINT 1 Task 1.1: Provision bare-metal infrastructure.

Give me step-by-step guidance on:
1. Creating Terraform code for Hetzner
2. Provisioning 3 servers (64GB RAM, 8 cores, NVMe)
3. Documenting the infrastructure

Show me the exact terraform/hetzner.tf code I should create.
```

---

## WHAT HAPPENS AFTER YOU PASTE THAT

Cursor will:
1. Guide you through Task 1.1 (infrastructure provisioning)
2. Once complete, you ask: "Guide me through SPRINT 1 Task 1.2"
3. It guides Task 1.2 (Talos Linux + K3s)
4. Continue for all 8 sprints, one task at a time

**Each sprint takes ~2 weeks of actual work**

---

## FASTEST POSSIBLE START

**Copy-paste these 2 things in order:**

### Thing 1: Push to GitHub
```bash
cd F:\aia
git init
git remote add origin https://github.com/serverax/aia.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

### Thing 2: Open in Cursor & Start
```bash
cursor F:\aia
```

Then in Cursor chat, paste the **CURSOR MASTER PROMPT** above.

---

## THE SPRINT PROGRESSION

**Sprint 1 (Weeks 1-2)**: Infrastructure
- Task 1.1: Bare-metal servers ← Start here
- Task 1.2: Talos + K3s
- Task 1.3: Redis
- Task 1.4: PostgreSQL
- Task 1.5: OpenTelemetry
- Task 1.6: Echo Agent
- Task 1.7: Tests

**Sprint 2 (Weeks 3-4)**: Orchestration
- Task 2.1: Orchestrator Agent
- Task 2.2: Compliance Officer
- Task 2.3: Conflict Resolution
- Task 2.4: Integration Tests

**Sprint 3 (Weeks 5-7)**: RAG & Knowledge
- Task 3.1: Qdrant setup
- Task 3.2: Milvus setup
- Task 3.3: Tool integration
- Task 3.4: Determinism tests

**Sprint 4 (Weeks 8-9)**: Frontend
- Task 4.1: WebSocket server
- Task 4.2: React dashboard
- Task 4.3: Approval gate UI

**Sprint 5 (Weeks 10-11)**: Document Finalization
- Task 5.1: Editor Agent
- Task 5.2: Template system

**Sprint 6 (Weeks 12-13)**: Wasm Security
- Task 6.1: WasmEdge integration
- Task 6.2: Tool sandboxing
- Task 6.3: Artifact signing

**Sprint 7 (Weeks 14-15)**: Compliance Controls
- Task 7.1: Kill-Switch API
- Task 7.2: Compliance middleware

**Sprint 8 (Week 16)**: Production Hardening
- Task 8.1: Load testing
- Task 8.2: Security audit
- Task 8.3: SLA definition

---

## FOR EACH TASK, USE THIS WORKFLOW

1. **Read the sprint document**
   ```
   Read: SPRINT_1_INFRASTRUCTURE.md Task 1.1
   ```

2. **Ask Cursor to guide you**
   ```
   Guide me through SPRINT_1 Task 1.1: Provision bare-metal infrastructure.
   Reference: SPRINT_1_INFRASTRUCTURE.md Task 1.1
   ```

3. **Implement the code** (Cursor will show you exactly what to create)

4. **Test it**
   ```
   pytest tests/
   ```

5. **Commit to Git**
   ```
   git add .
   git commit -m "Sprint 1 Task 1.1: Infrastructure provisioning"
   git push origin main
   ```

6. **Move to next task**
   ```
   Guide me through SPRINT_1 Task 1.2: Install Talos Linux and K3s.
   ```

---

## ESTIMATED TIMELINE

- **30 minutes**: Push to GitHub + open in Cursor
- **2 weeks per sprint**: Active implementation
- **16 weeks total**: All 8 sprints complete
- **Final result**: Production-ready Synthetic Enterprise system

---

## SUCCESS CRITERIA

### After Sprint 1
- [ ] K3s cluster running (3 nodes healthy)
- [ ] Redis working (streams + pub/sub)
- [ ] PostgreSQL running (audit log immutable)
- [ ] Echo Agent responding to messages

### After Sprint 2
- [ ] Orchestrator decomposing tasks
- [ ] Compliance Officer reviewing outputs
- [ ] Analyst processing requests
- [ ] Multi-agent routing working

### After Sprint 3
- [ ] Qdrant indexed with UK legislation
- [ ] Milvus partitioned by client
- [ ] Tools integrated (web search, document fetch)
- [ ] >95% determinism verified

### After Sprint 4
- [ ] Real-time WebSocket updates
- [ ] React dashboard showing agent status
- [ ] Approval gate for escalations

### After Sprint 5
- [ ] Document generation working
- [ ] DOCX/PDF output from templates

### After Sprint 6
- [ ] WasmEdge sandbox running
- [ ] Tools signed with Cosign
- [ ] All tools execute in Wasm

### After Sprint 7
- [ ] Kill-Switch API operational
- [ ] Compliance middleware enforcing permissions

### After Sprint 8
- [ ] Load tests passing (100+ req/min)
- [ ] Security audit complete
- [ ] SLA defined and documented
- **✅ PRODUCTION READY**

---

## ONE-LINER QUICK START

```bash
cd F:\aia && git init && git remote add origin https://github.com/serverax/aia.git && git add . && git commit -m "Initial" && git push -u origin main && cursor .
```

Then paste the **CURSOR MASTER PROMPT** (see above) into Cursor chat.

---

## THAT'S IT!

You now have:
✅ Everything pushed to GitHub  
✅ Cursor ready to guide all 8 sprints  
✅ Clear task-by-task workflow  
✅ Success criteria for each sprint  

**Start now. Follow Cursor's guidance. 16 weeks to production.** 🚀

