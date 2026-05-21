# SPRINTS_3_THROUGH_8.md: Remaining Development Phases (Weeks 5–16)

This document consolidates Sprints 3–8 technical specifications in a structured format for senior developer implementation.

---

## SPRINT 3: RAG & DOMAIN KNOWLEDGE (Weeks 5–7)

### Objective
Populate agents with real data: UK legislation, case law, client data. Test RAG accuracy and relevance scoring.

### Key Deliverables

#### 3.1 Qdrant Deployment (Compliance Officer Knowledge)
**Task**: Deploy isolated Qdrant instance for UK legal databases.

**Implementation**:
```bash
# Helm chart deployment
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm install qdrant qdrant/qdrant \
  --namespace data-layer \
  --values infrastructure/helm-charts/qdrant-values.yaml
```

**Schema** (`libs/communication/qdrant_schema.md`):
- Collection: `uk_compliance`
  - Vectors: 1536-dim (text-embedding-3-small via OpenAI or Claude embeddings)
  - Payload: `{regulation, section, jurisdiction, source, last_updated, text}`
  - Filter: `jurisdiction == "UK"`

**Data Ingestion** (`services/compliance-agent/qdrant_indexer.py`):
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import requests

class QdrantIndexer:
    def __init__(self):
        self.client = QdrantClient(url="http://qdrant:6333")
    
    def create_collection(self):
        """Create UK compliance collection."""
        self.client.create_collection(
            collection_name="uk_compliance",
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
    
    def index_legislation(self):
        """Fetch and index UK legislation from legislation.gov.uk API."""
        
        # Example: Employment Rights Act 1996
        acts = [
            {
                'url': 'https://www.legislation.gov.uk/ukpga/1996/23/contents',
                'title': 'Employment Rights Act 1996'
            }
        ]
        
        for act in acts:
            response = requests.get(f"{act['url']}/data.json")
            sections = response.json()['sections']
            
            for section in sections:
                embedding = embed_text(section['text'])
                point = PointStruct(
                    id=hash(section['id']),
                    vector=embedding,
                    payload={
                        'regulation': act['title'],
                        'section': section['id'],
                        'text': section['text'],
                        'jurisdiction': 'UK',
                        'source': act['url']
                    }
                )
                self.client.upsert(
                    collection_name="uk_compliance",
                    points=[point]
                )
    
    def index_sra_guidance(self):
        """Index SRA Regulatory and Conduct Guidance."""
        # Similar pattern; fetch from sra.org.uk
        pass
```

**Testing** (`services/compliance-agent/test_qdrant.py`):
```python
def test_qdrant_search():
    """Test that Qdrant returns relevant regulations."""
    
    query = "settlement agreement employment"
    results = client.search(
        collection_name="uk_compliance",
        query_vector=embed_text(query),
        limit=5
    )
    
    # Verify results are employment law
    for result in results:
        assert "Employment" in result.payload['regulation']
        assert result.score > 0.7
```

---

#### 3.2 Milvus Deployment (Analyst Domain Knowledge)
**Task**: Deploy Milvus for client-specific data + industry precedents.

**Implementation**:
```bash
helm repo add milvus https://milvus-io.github.io/milvus-helm
helm install milvus milvus/milvus \
  --namespace data-layer \
  --values infrastructure/helm-charts/milvus-values.yaml
```

**Client Partitioning** (`services/analyst-agent/milvus_manager.py`):
```python
from pymilvus import Collection, connections, CollectionSchema, FieldSchema, DataType

def create_client_partition(client_id: str):
    """Create isolated partition for client data."""
    
    connections.connect("default", host="milvus", port="19530")
    
    # Schema
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65536),
        FieldSchema(name="document_type", dtype=DataType.VARCHAR),
        FieldSchema(name="created_at", dtype=DataType.INT64),
    ]
    
    schema = CollectionSchema(fields, f"Client {client_id} data")
    collection = Collection(f"client_{client_id}", schema)
    
    # Create partition (for additional isolation)
    collection.create_partition(f"{client_id}_partition")
    
    return collection

def insert_client_document(client_id: str, doc_id: str, text: str, doc_type: str):
    """Insert client document with embedding."""
    
    collection = Collection(f"client_{client_id}")
    embedding = embed_text(text)
    
    entities = [
        [doc_id],
        [embedding],
        [text],
        [doc_type],
        [int(time.time() * 1000)]
    ]
    
    collection.insert(entities, partition_name=f"{client_id}_partition")
    collection.flush()
```

**Hybrid Search** (`services/analyst-agent/rag.py`):
```python
def hybrid_search(client_id: str, query: str, top_k: int = 5):
    """Hybrid search: semantic + BM25 keyword."""
    
    collection = Collection(f"client_{client_id}")
    
    # Semantic search
    query_embedding = embed_text(query)
    semantic_results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "L2", "params": {"nprobe": 16}},
        limit=20,
        partition_names=[f"{client_id}_partition"]
    )
    
    # BM25 (keyword) search - requires elasticsearch integration
    keyword_results = es_client.search(
        index=f"client_{client_id}",
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text"]
                }
            },
            "size": 20
        }
    )
    
    # Merge and deduplicate
    combined = {}
    for result in semantic_results[0]:
        combined[result.id] = {'semantic_score': result.score}
    
    for hit in keyword_results['hits']['hits']:
        if hit['_id'] in combined:
            combined[hit['_id']]['keyword_score'] = hit['_score']
        else:
            combined[hit['_id']] = {'keyword_score': hit['_score']}
    
    # Rerank with Cohere
    docs = [combined[doc_id] for doc_id in combined.keys()]
    reranked = cohere.rerank(
        model="rerank-english-v2.0",
        query=query,
        documents=[doc['text'] for doc in docs],
        top_k=top_k
    )
    
    return reranked
```

---

#### 3.3 Tool Integration
**Task**: Implement web search, document retrieval, threat intelligence tools.

**Web Search Tool**:
```python
# libs/communication/tools.py

import httpx

async def web_search(query: str, num_results: int = 10) -> list[dict]:
    """Search web using DuckDuckGo API."""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json"},
            timeout=10
        )
        data = response.json()
        
        return [
            {
                "title": result.get("Title"),
                "url": result.get("FirstURL"),
                "snippet": result.get("Result"),
                "retrieved_at": datetime.utcnow().isoformat()
            }
            for result in data.get("Results", [])[:num_results]
        ]
```

**Document Retrieval Tool**:
```python
async def fetch_document(client_id: str, doc_id: str) -> str:
    """Retrieve document from client vault (Milvus or S3)."""
    
    # Fetch from Milvus
    collection = Collection(f"client_{client_id}")
    results = collection.query(f"id == '{doc_id}'")
    
    if results:
        return results[0]['text']
    
    raise ValueError(f"Document {doc_id} not found")
```

**Threat Intelligence Tool**:
```python
async def lookup_cvss_score(cve_id: str) -> dict:
    """Look up CVE severity score."""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.nvd.nist.gov/rest/json/cves/1.0/{cve_id}",
            timeout=10
        )
        data = response.json()
        
        return {
            "cve_id": cve_id,
            "cvss_score": data.get("cve", {}).get("impact", {}).get("baseMetricV3", {}).get("cvssV3", {}).get("baseSeverity"),
            "description": data.get("cve", {}).get("description", {}).get("description_data", [{}])[0].get("value")
        }
```

---

#### 3.4 Deterministic Evaluation
**Task**: Create benchmark test suite. All agent outputs must be 100% deterministic (temperature=0).

**Evals Framework** (`libs/evaluation/determinism_evals.py`):
```python
import json
from services.analyst_agent.main import AnalystAgent

def test_determinism():
    """Run same request 5 times; verify identical output."""
    
    agent = AnalystAgent()
    
    request = {
        "task_id": "test_task_1",
        "query": "Analyze indemnification clause in contract",
        "document": "..."
    }
    
    outputs = []
    for i in range(5):
        output = agent.process_task(request)
        outputs.append(json.dumps(output, sort_keys=True))
    
    # All outputs must be identical
    assert all(output == outputs[0] for output in outputs), \
        "Agent outputs are non-deterministic!"
    
    print("✓ Determinism test passed")
```

**Benchmark Dataset** (`tests/evals/benchmark_requests.json`):
```json
[
  {
    "id": "eval_1",
    "type": "contract_review",
    "query": "Review settlement agreement for GDPR compliance",
    "document_id": "settlement_v3.pdf",
    "expected_findings_min": 1,
    "expected_risk_level": "amber"
  },
  {
    "id": "eval_2",
    "type": "precedent_research",
    "query": "Find 3 settlement agreements with severance >£50k",
    "expected_results_min": 3
  }
]
```

---

### Sprint 3 Acceptance Criteria
- ✅ Qdrant deployed with UK legislation indexed (500+ regulations)
- ✅ Milvus deployed with client partition isolation
- ✅ Hybrid search (semantic + BM25) working
- ✅ Web search, document fetch, threat intelligence tools functional
- ✅ Determinism tests: 95%+ consistency across 5 runs
- ✅ Agent outputs include proper citations
- ✅ Confidence scoring implemented and tested

---

## SPRINT 4: GLASS BOX UI & HUMAN-IN-THE-LOOP (Weeks 8–9)

### Objective
Build real-time frontend dashboard. Users watch agents work. Approval gates functional.

### Key Deliverables

#### 4.1 Real-Time WebSocket Server
**File**: `apps/api-gateway/websocket_server.py`

```python
from fastapi import FastAPI, WebSocket
import asyncio
import json
import redis

app = FastAPI()

async def broadcast_updates(project_id: str, ws: WebSocket):
    """Stream agent status updates to frontend."""
    
    redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f'ui:updates:{project_id}')
    
    while True:
        message = pubsub.get_message()
        if message and message['type'] == 'message':
            await ws.send_json(json.loads(message['data']))
        await asyncio.sleep(0.1)

@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await websocket.accept()
    try:
        await broadcast_updates(project_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()
```

#### 4.2 React Dashboard Components
**File**: `apps/web-dashboard/src/components/AgentMonitor.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import useWebSocket from 'react-use-websocket';

const AgentMonitor: React.FC<{ projectId: string }> = ({ projectId }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Record<string, AgentStatus>>({});
  
  const { lastJsonMessage } = useWebSocket(`ws://localhost:8000/ws/${projectId}`);
  
  useEffect(() => {
    if (!lastJsonMessage) return;
    
    const message = lastJsonMessage as StatusUpdate;
    
    // Update task graph
    setTasks(prev => prev.map(task => 
      task.id === message.task_id 
        ? { ...task, status: message.status }
        : task
    ));
    
    // Update agent status
    setAgents(prev => ({
      ...prev,
      [message.agent_id]: {
        status: message.status,
        current_task: message.task_id,
        last_update: new Date()
      }
    }));
  }, [lastJsonMessage]);
  
  return (
    <div className="agent-monitor">
      <h2>Agent Status</h2>
      {Object.entries(agents).map(([agent, status]) => (
        <div key={agent} className="agent-card">
          <h3>{agent}</h3>
          <p>Status: <span className={`status-${status.status}`}>{status.status}</span></p>
          <p>Current Task: {status.current_task}</p>
        </div>
      ))}
      
      <h2>Task Graph</h2>
      <div className="task-graph">
        {tasks.map(task => (
          <TaskNode key={task.id} task={task} />
        ))}
      </div>
    </div>
  );
};

export default AgentMonitor;
```

#### 4.3 Approval Gate UI
**File**: `apps/web-dashboard/src/components/ApprovalGate.tsx`

```typescript
const ApprovalGate: React.FC<{ escalation: Escalation }> = ({ escalation }) => {
  const [decision, setDecision] = useState<'approve' | 'revise' | 'reject' | null>(null);
  
  const handleApprove = async () => {
    await fetch(`/api/escalations/${escalation.id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ decision: 'approve' })
    });
    setDecision('approve');
  };
  
  return (
    <div className="approval-gate" style={{ border: '3px solid red' }}>
      <h2>APPROVAL REQUIRED</h2>
      
      <div className="conflict-panel">
        <TwoColumnDebate
          left={{
            agent: escalation.agent_a,
            position: escalation.position_a
          }}
          right={{
            agent: escalation.agent_b,
            position: escalation.position_b
          }}
        />
      </div>
      
      <div className="action-buttons">
        <button onClick={handleApprove} className="btn-approve">
          ✓ APPROVE
        </button>
        <button onClick={() => setDecision('revise')} className="btn-revise">
          ↻ REQUEST REVISION
        </button>
        <button onClick={() => setDecision('reject')} className="btn-reject">
          ✗ REJECT
        </button>
      </div>
      
      {decision && <p>Decision recorded: {decision}</p>}
    </div>
  );
};
```

---

## SPRINT 5: EDITOR & DOCUMENT FINALIZATION (Weeks 10–11)

### Objective
Editor Agent formats outputs into professional DOCX/PDF. Document generation pipeline complete.

### Key Deliverables

#### 5.1 Editor Agent Implementation
**File**: `services/editor-agent/main.py`

```python
class EditorAgent:
    def __init__(self):
        self.templates = load_templates('infrastructure/templates/')
    
    async def format_document(self, task_data: Dict) -> str:
        """Convert raw output to professional document."""
        
        # Apply template
        template = self.templates['settlement_agreement']
        
        doc = Document()
        doc.add_heading('Settlement Agreement', 0)
        doc.add_paragraph(task_data['preamble'])
        
        for clause in task_data['clauses']:
            doc.add_heading(clause['title'], level=1)
            doc.add_paragraph(clause['content'])
        
        # Save to DOCX
        output_path = f"/tmp/{task_data['task_id']}.docx"
        doc.save(output_path)
        
        return output_path
    
    async def generate_pdf(self, docx_path: str) -> str:
        """Convert DOCX to PDF using Pandoc."""
        
        pdf_path = docx_path.replace('.docx', '.pdf')
        subprocess.run(['pandoc', docx_path, '-o', pdf_path], check=True)
        
        return pdf_path
```

#### 5.2 Template System
**File**: `infrastructure/templates/settlement_agreement.json`

```json
{
  "title": "Settlement Agreement",
  "sections": [
    {
      "name": "Preamble",
      "template": "This Settlement Agreement is made between..."
    },
    {
      "name": "Severance",
      "template": "The Employer shall pay the Employee the sum of £{severance_amount}..."
    },
    {
      "name": "Confidentiality",
      "template": "The Employee agrees to keep confidential..."
    }
  ]
}
```

---

## SPRINT 6: WASM SECURITY LAYER (Weeks 12–13)

### Objective
Sandbox all agent-generated code execution. Cryptographic signing of all Wasm modules.

### Key Deliverables

#### 6.1 WasmEdge Integration
**File**: `infrastructure/helm-charts/wasmedge-runtime.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: wasmedge-policies
data:
  agent-execution-policy.yaml: |
    version: 1
    rules:
      - name: "domain-analyst"
        allowedCapabilities:
          - network_outbound
          - filesystem_read
        deniedCapabilities:
          - filesystem_write
          - process_exec
```

#### 6.2 Tool Sandboxing
**File**: `libs/communication/wasm_executor.py`

```python
from wasmtime import Engine, Module, Instance

def execute_tool_in_sandbox(tool_name: str, inputs: Dict) -> Dict:
    """Execute tool inside Wasm sandbox."""
    
    engine = Engine()
    module = Module(engine, open(f'tools/{tool_name}.wasm', 'rb').read())
    instance = Instance(engine, module, {})
    
    # Call tool with strict input validation
    result = instance.exports(engine)['execute'](
        json.dumps(inputs)
    )
    
    return json.loads(result)
```

#### 6.3 Artifact Signing
**File**: `infrastructure/ci/sign_wasm_artifacts.sh`

```bash
#!/bin/bash

# Build Wasm module
cargo build --target wasm32-unknown-unknown --release

# Sign with Cosign
cosign sign-blob \
  --key cosign.key \
  target/wasm32-unknown-unknown/release/agent_tool.wasm \
  > agent_tool.wasm.sig

# Verify signature on deployment
cosign verify-blob \
  --key cosign.pub \
  --signature agent_tool.wasm.sig \
  agent_tool.wasm
```

---

## SPRINT 7: COMPLIANCE CONTROLS & CONTAINMENT (Weeks 14–15)

### Objective
Implement Kill-Switch API. Regulatory controls for August 2026 readiness.

### Key Deliverables

#### 7.1 Kill-Switch API
**File**: `apps/api-gateway/admin_api.py`

```python
from fastapi import FastAPI, APIRouter, Depends
from libs.security.auth import require_admin_token

admin_router = APIRouter(prefix="/admin", tags=["administration"])

@admin_router.post("/agents/{agent_id}/pause")
async def pause_agent(agent_id: str, _: str = Depends(require_admin_token)):
    """Immediately pause an agent."""
    
    redis_client.publish(
        f'agent:{agent_id}:commands',
        json.dumps({'command': 'pause', 'reason': 'admin_request'})
    )
    
    # Log to audit
    audit_log.insert({
        'action': 'agent_paused',
        'agent_id': agent_id,
        'timestamp': datetime.utcnow(),
        'admin_user': current_user()
    })
    
    return {"status": "paused", "agent_id": agent_id}

@admin_router.post("/tools/{tool_id}/revoke")
async def revoke_tool_access(tool_id: str, _: str = Depends(require_admin_token)):
    """Revoke tool access in real-time."""
    
    # Update tool registry
    redis_client.hset(f'tool_access:{tool_id}', 'revoked', 'true')
    
    # Notify all agents
    redis_client.publish(
        'orchestrator:commands',
        json.dumps({
            'command': 'revoke_tool',
            'tool_id': tool_id
        })
    )
    
    return {"status": "revoked", "tool_id": tool_id}
```

#### 7.2 Compliance Middleware
**File**: `libs/communication/compliance_middleware.py`

```python
async def policy_enforcement_middleware(request):
    """Validate all tool calls against policy manifest."""
    
    agent_id = request.headers.get('X-Agent-ID')
    tool_id = request.json.get('tool')
    
    # Check if tool is allowed for this agent
    allowed_tools = redis_client.hgetall(f'agent_permissions:{agent_id}')
    
    if tool_id not in allowed_tools:
        logger.warning(f"Denied tool access: {agent_id} → {tool_id}")
        raise PermissionError(f"Tool {tool_id} not permitted for {agent_id}")
    
    # Check if tool is revoked
    if redis_client.hget(f'tool_access:{tool_id}', 'revoked'):
        raise PermissionError(f"Tool {tool_id} has been revoked")
    
    # Proceed
    return await request.next()
```

---

## SPRINT 8: PRODUCTION HARDENING & LAUNCH (Week 16)

### Objective
Load testing, security audit, SLA definition. Ready for market.

### Key Deliverables

#### 8.1 Load Testing
**File**: `infrastructure/tests/k6_load_test.js`

```javascript
import http from 'k6/http';
import { check, group } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 50 },   // Ramp up to 50
    { duration: '2m', target: 10 },   // Ramp down
  ],
};

export default function() {
  group('Submit Request', () => {
    const payload = {
      request: 'Draft a settlement agreement',
      project_id: `project_${__VU}_${__ITER}`
    };
    
    const response = http.post('http://localhost:8000/api/request', payload);
    
    check(response, {
      'status is 202': (r) => r.status === 202,
      'response time < 500ms': (r) => r.timings.duration < 500,
    });
  });
}
```

#### 8.2 Security Audit Checklist
**File**: `docs/SECURITY_AUDIT_CHECKLIST.md`

```markdown
# Security Audit Checklist (Sprint 8)

## Network Security
- [ ] All services behind TLS/mTLS
- [ ] NetworkPolicies enforce namespace isolation
- [ ] Ingress controller has rate limiting
- [ ] Secrets manager (Sealed Secrets) enabled

## Application Security
- [ ] Input validation on all APIs
- [ ] Output encoding (XSS prevention)
- [ ] SQL injection prevention (parameterized queries)
- [ ] CSRF tokens on state-changing requests

## Data Security
- [ ] Encryption at rest (etcd, PostgreSQL)
- [ ] Encryption in transit (TLS 1.3)
- [ ] Data deletion on project completion
- [ ] Audit log immutability verified

## Access Control
- [ ] RBAC for K3s resources
- [ ] Least privilege service accounts
- [ ] Admin API requires strong auth
- [ ] API key rotation policy

## Compliance
- [ ] GDPR Data Processing Agreement in place
- [ ] Incident response procedure documented
- [ ] Data retention policy implemented
- [ ] Audit trail complete and exportable
```

#### 8.3 SLA Definition
**File**: `docs/SERVICE_LEVEL_AGREEMENT.md`

```markdown
# Service Level Agreement

## Uptime Commitment
- **Target Availability**: 99.5% (measured over 30 days)
- **Maximum Planned Downtime**: 4 hours/month
- **Maximum Incident Duration**: 1 hour

## Performance Commitments
- **Request Latency (p95)**: < 60 seconds (user request → final output)
- **Message Delivery**: < 100ms (agent-to-agent message latency)
- **Approval Gate Response**: < 5 minutes (human approval)

## Cost Guarantees
- **Per-Request Cost**: < £5 (including LLM, infrastructure, observability)
- **Data Sovereignty**: All data processed in UK jurisdiction
- **No Data Sharing**: Client data never used for training or analytics

## Support & Escalation
- **Critical Issues**: 15-minute response SLA
- **High Priority**: 1-hour response SLA
- **Normal**: 4-hour response SLA
```

---

## CONSOLIDATED TESTING STRATEGY (ALL SPRINTS)

### Unit Tests
```bash
# Run all unit tests
pytest services/ libs/ -v --cov

# Expected coverage: >80%
```

### Integration Tests
```bash
# Run end-to-end workflows
bash infrastructure/tests/integration_test_full_workflow.sh

# Test scenarios:
# 1. Simple request → decompose → route → complete
# 2. Request with conflicts → escalate → human override
# 3. Agent failure → recovery from checkpoint
# 4. Pod restart → state recovered
```

### Performance Tests
```bash
# Load testing
k6 run infrastructure/tests/k6_load_test.js

# Benchmarks:
# - 10 concurrent users: <60s per request
# - 50 concurrent users: <80s per request
# - Throughput: >100 requests/minute
```

### Security Tests
```bash
# Container scanning
trivy scan docker_image:latest

# SAST (static analysis)
bandit services/ libs/ --recursive

# Network policy validation
./infrastructure/tests/validate_network_policies.sh
```

---

## DEPLOYMENT CHECKLIST (FINAL)

- ✅ All 8 sprints complete
- ✅ All unit tests passing (>80% coverage)
- ✅ All integration tests passing
- ✅ Load testing verified (100+ req/min sustainable)
- ✅ Security audit passed
- ✅ SLA defined and published
- ✅ Incident response playbook created
- ✅ Backup/restore tested (RTO: 1h, RPO: 15min)
- ✅ Runbooks documented (daily ops, troubleshooting)
- ✅ Team training completed
- ✅ Client on-boarding process defined

---

## POST-LAUNCH ROADMAP

### Month 1 (Post-Launch)
- Monitor production uptime (target: 99.5%)
- Collect user feedback
- Optimize common request paths
- Fix issues discovered in production

### Month 2
- Scale to 10+ concurrent clients
- Implement additional domain-specific agents (cybersecurity, finance)
- Add advanced RAG features (hierarchical chunking, semantic caching)

### Month 3–6
- Expand to EU/US markets
- Build additional agent personas (legal strategist, negotiations agent)
- Implement federated learning for better precedent discovery

---

**End of Sprints 3–8 Technical Specifications**

