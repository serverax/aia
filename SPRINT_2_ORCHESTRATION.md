# SPRINT_2_ORCHESTRATION.md: Multi-Agent Routing & State Management (Weeks 3–4)

## SPRINT OBJECTIVE

Build the **Orchestrator Agent** with task decomposition, multi-agent routing, and conflict resolution. Validate that the system can:

1. ✅ Accept a complex user request
2. ✅ Decompose it into subtasks
3. ✅ Route to appropriate specialist agents (Analyst, Compliance, Editor)
4. ✅ Track progress
5. ✅ Detect and resolve conflicts
6. ✅ Maintain a coherent task graph across multiple agents

**Success Metric**: A user request "Draft a settlement agreement" flows through Orchestrator → routes to Analyst & Compliance Officer → agents return results → Orchestrator detects any conflicts and escalates.

---

## TECHNICAL SCOPE

### New Components (Sprint 2)

```
┌──────────────────────────────────────────────────────────┐
│         ORCHESTRATION LAYER (NEW)                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │   Orchestrator Agent (LangGraph)                   │ │
│  │   ├─ Intent Parser                                │ │
│  │   ├─ Task Decomposer                              │ │
│  │   ├─ Router                                        │ │
│  │   ├─ Conflict Resolver                            │ │
│  │   └─ State Manager                                │ │
│  └────────────────────────────────────────────────────┘ │
└────────────┬──────────────────────────────────────────────┘
             │
     ┌───────┴───────────┬─────────────────┐
     ↓                   ↓                 ↓
  Analyst Agent    Compliance Agent    Editor Agent
  (from Sprint 1)  (NEW)               (PLACEHOLDER)
```

### Key Technologies

- **Framework**: LangGraph (Python)
- **State Store**: Redis (task graph persistence)
- **Message Broker**: Redis Streams (task queue + status updates)
- **LLM**: Claude Sonnet 4 (temperature=0)
- **Testing**: pytest + integration tests

---

## DETAILED TASKS

### TASK 2.1: Implement Orchestrator Agent with LangGraph (Days 1–2)

#### Deliverables
- `services/orchestrator-agent/` complete
- Accepts user requests; parses intent
- Decomposes into atomic tasks
- Returns task graph JSON

#### Implementation Guide

1. **Install LangGraph**:
   ```bash
   pip install langgraph langchain langchain-anthropic
   ```

2. **Create State Schema** (`services/orchestrator-agent/state.py`):
   ```python
   from typing import Dict, List, Any, Optional
   from dataclasses import dataclass, field
   from enum import Enum
   
   class TaskStatus(str, Enum):
       PENDING = "pending"
       IN_PROGRESS = "in_progress"
       COMPLETED = "completed"
       FAILED = "failed"
       ESCALATED = "escalated"
   
   class AgentType(str, Enum):
       ANALYST = "domain_analyst"
       COMPLIANCE = "compliance_officer"
       EDITOR = "editor"
   
   @dataclass
   class Task:
       id: str
       name: str
       description: str
       assigned_to: AgentType
       status: TaskStatus = TaskStatus.PENDING
       inputs: Dict[str, Any] = field(default_factory=dict)
       expected_outputs: List[str] = field(default_factory=list)
       depends_on: List[str] = field(default_factory=list)
       priority: str = "normal"
       deadline: Optional[str] = None
       result: Optional[Dict[str, Any]] = None
       error: Optional[str] = None
   
   @dataclass
   class OrchestratorState:
       user_request: str
       project_id: str
       
       # Intent parsing
       intent_parsed: Optional[Dict[str, Any]] = None
       ambiguities: List[str] = field(default_factory=list)
       requires_clarification: bool = False
       
       # Task decomposition
       tasks: List[Task] = field(default_factory=list)
       task_graph: Dict[str, Task] = field(default_factory=dict)
       
       # Execution state
       current_phase: str = "parsing"  # parsing → decomposing → routing → executing
       completed_tasks: List[str] = field(default_factory=list)
       failed_tasks: List[str] = field(default_factory=list)
       
       # Conflict tracking
       conflicts: List[Dict[str, Any]] = field(default_factory=list)
       
       # Messages
       messages: List[Dict[str, Any]] = field(default_factory=list)
   ```

3. **Create Intent Parser Node** (`services/orchestrator-agent/nodes.py`):
   ```python
   import json
   from langchain_anthropic import ChatAnthropic
   from state import OrchestratorState, TaskStatus
   
   def intent_parser_node(state: OrchestratorState) -> OrchestratorState:
       """Parse user request into structured intent."""
       
       llm = ChatAnthropic(
           model="claude-sonnet-4-20250514",
           temperature=0
       )
       
       prompt = f"""
       You are an intent parser. Your job is to extract the user's request into a structured format.
       
       USER REQUEST:
       {state.user_request}
       
       Respond ONLY with valid JSON (no markdown, no explanations):
       {{
           "objective": "...",
           "domain": "employment_law|contract_law|cybersecurity|finance|general",
           "scope": "...",
           "constraints": [...],
           "ambiguities": [...],
           "requires_clarification": true|false,
           "clarification_questions": [...]
       }}
       """
       
       response = llm.invoke(prompt)
       intent = json.loads(response.content)
       
       state.intent_parsed = intent
       state.ambiguities = intent.get('ambiguities', [])
       state.requires_clarification = intent.get('requires_clarification', False)
       state.current_phase = "decomposing" if not state.requires_clarification else "awaiting_clarification"
       
       return state
   
   def task_decomposer_node(state: OrchestratorState) -> OrchestratorState:
       """Decompose intent into atomic tasks."""
       
       if state.requires_clarification:
           return state  # Skip decomposition if clarification needed
       
       llm = ChatAnthropic(
           model="claude-sonnet-4-20250514",
           temperature=0
       )
       
       prompt = f"""
       You are a task decomposer. Your job is to break a complex objective into atomic subtasks.
       
       OBJECTIVE: {state.intent_parsed['objective']}
       DOMAIN: {state.intent_parsed['domain']}
       CONSTRAINTS: {json.dumps(state.intent_parsed['constraints'])}
       
       Each task should be assigned to one of these agents:
       - domain_analyst: Research, analysis, evidence gathering
       - compliance_officer: Regulatory verification, risk flagging
       - editor: Formatting, document finalization
       
       Respond ONLY with valid JSON:
       {{
           "tasks": [
               {{
                   "id": "task_1",
                   "name": "...",
                   "description": "...",
                   "assigned_to": "domain_analyst|compliance_officer|editor",
                   "inputs": {{}},
                   "expected_outputs": [...],
                   "depends_on": [],
                   "priority": "critical|high|normal",
                   "deadline": "ISO8601 or null"
               }}
           ]
       }}
       """
       
       response = llm.invoke(prompt)
       decomposition = json.loads(response.content)
       
       # Build task objects and dependency graph
       for task_data in decomposition['tasks']:
           task = Task(**task_data)
           state.task_graph[task.id] = task
           state.tasks.append(task)
       
       state.current_phase = "routing"
       
       return state
   ```

4. **Create Router Node** (`services/orchestrator-agent/router.py`):
   ```python
   import json
   import redis
   from state import OrchestratorState, AgentType
   
   async def router_node(state: OrchestratorState) -> OrchestratorState:
       """Route tasks to appropriate agents via Redis."""
       
       redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
       
       for task in state.tasks:
           # Check dependencies
           dependencies_met = all(
               dep_id in state.completed_tasks 
               for dep_id in task.depends_on
           )
           
           if not dependencies_met:
               continue  # Skip task until dependencies are ready
           
           # Publish task assignment to Redis stream
           message = {
               'task_id': task.id,
               'name': task.name,
               'description': task.description,
               'assigned_to': task.assigned_to,
               'inputs': task.inputs,
               'expected_outputs': task.expected_outputs,
               'project_id': state.project_id
           }
           
           stream_name = f'agent:{task.assigned_to}:tasks'
           redis_client.xadd(stream_name, message)
           
           task.status = TaskStatus.IN_PROGRESS
       
       state.current_phase = "executing"
       
       return state
   ```

5. **Create LangGraph Workflow**:
   ```python
   # services/orchestrator-agent/graph.py
   from langgraph.graph import StateGraph, END
   from state import OrchestratorState
   from nodes import intent_parser_node, task_decomposer_node
   from router import router_node
   
   def create_orchestrator_graph():
       """Build the Orchestrator LangGraph."""
       
       graph = StateGraph(OrchestratorState)
       
       # Add nodes
       graph.add_node("intent_parser", intent_parser_node)
       graph.add_node("task_decomposer", task_decomposer_node)
       graph.add_node("router", router_node)
       graph.add_node("monitor", monitor_node)  # Polls for task completion
       
       # Add edges
       graph.add_edge("intent_parser", "task_decomposer")
       graph.add_edge("task_decomposer", "router")
       graph.add_edge("router", "monitor")
       
       # Conditional edge: if conflict detected, escalate
       graph.add_conditional_edges(
           "monitor",
           should_escalate,
           {
               True: "escalation_handler",
               False: "complete"
           }
       )
       
       graph.add_edge("escalation_handler", END)
       graph.add_edge("complete", END)
       
       graph.set_entry_point("intent_parser")
       
       return graph.compile()
   ```

---

### TASK 2.2: Build Compliance Officer Agent (Skeleton) (Days 2–3)

#### Deliverables
- `services/compliance-agent/` created
- Can receive tasks from Orchestrator
- Implements Qdrant RAG connection (placeholder)
- Returns compliance decision

#### Implementation Guide

1. **Skeleton Code** (`services/compliance-agent/main.py`):
   ```python
   """
   Compliance Officer Agent: Regulatory verification and risk flagging.
   """
   
   import json
   import redis
   from typing import Dict, Any
   from libs.communication.protocol import create_message
   
   class ComplianceOfficer:
       def __init__(self):
           self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
           self.agent_id = "compliance_officer_v1"
       
       def listen_for_tasks(self):
           """Main loop: listen for task assignments."""
           print(f"[{self.agent_id}] Ready to receive tasks")
           
           while True:
               messages = self.redis_client.xread(
                   {'agent:compliance_officer:tasks': '0'},
                   block=5000
               )
               
               if not messages:
                   continue
               
               for stream, entries in messages:
                   for message_id, data in entries:
                       self.process_compliance_check(message_id, data)
       
       def process_compliance_check(self, message_id: str, data: Dict[str, Any]):
           """Review document for regulatory compliance."""
           
           task_id = data.get('task_id')
           document_to_review = data.get('document', '')
           
           # Placeholder: In Sprint 3, this will query Qdrant
           compliance_result = {
               'task_id': task_id,
               'status': 'approved',  # placeholder
               'risk_level': 'green',
               'flags': []
           }
           
           # Publish result
           message = create_message(
               from_agent=self.agent_id,
               to_agent='orchestrator',
               task_id=task_id,
               message_type='task_complete',
               status='completed',
               data=compliance_result
           )
           
           self.redis_client.xadd(
               f'task_queue:{data.get("project_id")}',
               message
           )
   
   if __name__ == '__main__':
       officer = ComplianceOfficer()
       officer.listen_for_tasks()
   ```

2. **Dockerfile & K3s deployment similar to Echo Agent**

---

### TASK 2.3: Implement Conflict Detection & Resolution (Days 3–4)

#### Deliverables
- Orchestrator detects contradictory messages from agents
- "Debate Protocol" implemented (ask agents for rationale)
- Escalation to human when unresolved
- Conflict log stored in PostgreSQL

#### Implementation Guide

1. **Conflict Detector**:
   ```python
   # services/orchestrator-agent/conflict_detector.py
   
   def detect_conflict(agent1_result: Dict, agent2_result: Dict) -> Optional[Dict]:
       """
       Detect if two agent results contradict.
       
       Example:
       - Analyst says: "Settlement is complete and ready"
       - Compliance says: "GDPR violation detected"
       
       Return: conflict dict or None if no conflict
       """
       
       # Check for explicit rejection vs approval
       if agent1_result.get('status') == 'approved' and agent2_result.get('status') == 'rejected':
           return {
               'type': 'approval_conflict',
               'agent1': agent1_result.get('from_agent'),
               'agent2': agent2_result.get('from_agent'),
               'agent1_position': agent1_result.get('rationale'),
               'agent2_position': agent2_result.get('rationale')
           }
       
       return None
   
   def resolve_conflict(conflict: Dict, orchestrator_state: OrchestratorState):
       """
       Attempt to resolve conflict.
       
       1. Ask Agent 1 to respond to Agent 2's concerns
       2. If resolved, proceed
       3. If not, escalate to human
       """
       
       # Create debate task for Agent 1
       debate_prompt = f"""
       The {conflict['agent2']} agent has raised a concern:
       
       {conflict['agent2_position']}
       
       Please address this concern and either:
       A) Agree with their point and revise your position
       B) Provide evidence supporting your original position
       
       Respond with JSON:
       {{
           "response_to_concern": "...",
           "position": "agree|disagree",
           "evidence": [...]
       }}
       """
       
       # Send debate prompt; wait for response
       # If still unresolved after 2 rounds, escalate
   ```

2. **Escalation Handler**:
   ```python
   def escalate_to_human(conflict: Dict, project_id: str):
       """Escalate conflict to human for decision."""
       
       escalation_record = {
           'project_id': project_id,
           'type': 'agent_conflict',
           'agents': [conflict['agent1'], conflict['agent2']],
           'issue': conflict.get('type'),
           'position_a': conflict.get('agent1_position'),
           'position_b': conflict.get('agent2_position'),
           'required_action': 'Human must choose: revise or override'
       }
       
       # Save to PostgreSQL audit log
       # Publish to WebSocket for UI notification
       # Store in Redis for human review queue
   ```

---

### TASK 2.4: Integration Test: End-to-End Workflow (Days 4–5)

#### Deliverables
- Test script that:
  1. Submits a user request to Orchestrator
  2. Verifies task decomposition
  3. Routes to agents
  4. Collects results
  5. Verifies state consistency

#### Implementation Guide

```bash
#!/bin/bash
# infrastructure/tests/sprint2_orchestration_test.sh

set -e

echo "=== Sprint 2: Orchestration Test ==="

# 1. Deploy Orchestrator + Compliance Agent
kubectl apply -f services/orchestrator-agent/k8s-deployment.yaml
kubectl apply -f services/compliance-agent/k8s-deployment.yaml
kubectl wait --for=condition=ready pod -l app=orchestrator-agent --timeout=60s
kubectl wait --for=condition=ready pod -l app=compliance-officer --timeout=60s

# 2. Send user request
USER_REQUEST='{"request":"Draft a settlement agreement for disputed termination","project_id":"test_proj_1"}'

RESPONSE=$(kubectl run redis-client --image=redis:latest --rm -it -- \
  redis-cli -h redis.data-layer \
    XADD orchestrator:requests "*" \
      request "$USER_REQUEST")

echo "Request submitted: $RESPONSE"

# 3. Wait for orchestrator to decompose
sleep 3

# 4. Verify task graph in Redis
TASK_GRAPH=$(kubectl run redis-client --image=redis:latest --rm -it -- \
  redis-cli -h redis.data-layer \
    GET task_graph:test_proj_1)

echo "Task graph: $TASK_GRAPH"

# 5. Verify tasks routed to agents
ANALYST_TASKS=$(kubectl run redis-client --image=redis:latest --rm -it -- \
  redis-cli -h redis.data-layer \
    XLEN agent:domain_analyst:tasks)

COMPLIANCE_TASKS=$(kubectl run redis-client --image=redis:latest --rm -it -- \
  redis-cli -h redis.data-layer \
    XLEN agent:compliance_officer:tasks)

echo "Analyst tasks: $ANALYST_TASKS"
echo "Compliance tasks: $COMPLIANCE_TASKS"

if [ "$ANALYST_TASKS" -gt 0 ] && [ "$COMPLIANCE_TASKS" -gt 0 ]; then
  echo "✓ Tasks successfully routed to agents"
else
  echo "✗ Tasks not routed correctly"
  exit 1
fi

echo "=== Sprint 2 test passed ==="
```

---

### TASK 2.5: Documentation (Day 5)

#### Deliverables
- `services/orchestrator-agent/README.md`
- `docs/ORCHESTRATION_PROTOCOL.md` (detailed message specs)
- `docs/LANGGRAPH_PATTERNS.md` (how to use LangGraph for agents)

---

## SPRINT 2 ACCEPTANCE CHECKLIST

- ✅ Orchestrator Agent code complete (intent parsing + decomposition)
- ✅ Compliance Officer Agent skeleton + message handling
- ✅ LangGraph graph defined and tested
- ✅ Conflict detection logic implemented
- ✅ Escalation to human working
- ✅ Integration test passes (decomposition → routing → result collection)
- ✅ All agents publishing messages to Redis correctly
- ✅ State persisted in Redis (task graph recovery)

---

## SPRINT 2 RISKS

| Risk | Mitigation |
|------|-----------|
| **LangGraph learning curve** | Have architect review; pair programming for complex logic |
| **State synchronization issues** | Use Redis transactions; test concurrent updates |
| **Circular dependencies in task graph** | Implement topological sort validation |

---

**Next Sprint**: SPRINT_3_RAG_KNOWLEDGE.md

