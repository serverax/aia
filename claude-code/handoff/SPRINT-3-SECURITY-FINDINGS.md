# Sprint 3 Security Handoff — Findings from Sprint 6 audit

**To:** Gemini (Sprint 3 owner)
**From:** Claude Code (Sprint 6)
**Date:** 2026-05-21
**Status:** Must address before Sprint 3 PR merges

The Sprint 6 quality audit (`bandit -r services/ scripts/ libs/ -ll`) surfaced
one **High-severity** issue in code that's currently in `services/semantic_search/`
and `services/analyst_agent/` — both stubs you'll be filling in for Sprint 3.

Filing this as a formal handoff so the issue doesn't slip into the Sprint 3 PR.

---

## Finding 1 — `pickle.load()` on untrusted vector-store payloads (HIGH)

### Location
`services/semantic_search/vector_store/faiss_store.py:141`

### Code
```python
def load(self, path: str):
    """Load index and metadata from disk."""
    self.index = faiss.read_index(os.path.join(path, "index.faiss"))

    with open(os.path.join(path, "data.pkl"), "rb") as f:
        data = pickle.load(f)            # ← CWE-502

    self.metadata_store = data["metadata_store"]
    self.id_map = data["id_map"]
    self.str_to_int_id = data["str_to_int_id"]
```

### Why this is a problem

`pickle.load` deserializes **arbitrary Python objects**, including those that
execute code on unpickling (via `__reduce__`, `__setstate__`, etc.). Any entity
that can write `data.pkl` to the vector-store directory gets remote code execution
inside the agent pod. This breaks the Sprint 6 sandbox model end-to-end — the
agent has full namespace egress + Postgres write access + (in the case of
Analyst) Anthropic API key access.

Threat model relevance:
- **Tenant data poisoning:** if multi-tenant indexes share a filesystem mount (likely with Milvus on a PVC), a tenant who can write to one shard owns the agent that loads it.
- **Supply-chain compromise:** if vector indexes are ever fetched from external storage (S3, registry, etc.), the pickle is an RCE primitive on every download.
- **Backup/restore:** restoring from any uncontrolled snapshot deserializes whatever the snapshot contains.

CWE-502: https://cwe.mitre.org/data/definitions/502.html

### Required remediation (pick one)

**Option A — `safetensors` (recommended for ML metadata)**
```python
from safetensors.numpy import save_file, load_file

# Save
save_file({"metadata": np.array(...), "id_map": np.array(...)}, "data.safetensors")

# Load
data = load_file("data.safetensors")
```
- Format is purely declarative tensors; no code execution surface.
- Industry standard for ML model + metadata serialization in 2026.
- Already a transitive dep of HuggingFace tooling we'll pull in.

**Option B — JSON + numpy.save split**
```python
# Save (deterministic, human-readable for metadata)
np.save(os.path.join(path, "id_map.npy"), self.id_map)
with open(os.path.join(path, "metadata.json"), "w") as f:
    json.dump(self.metadata_store, f)

# Load
id_map = np.load(os.path.join(path, "id_map.npy"))
with open(os.path.join(path, "metadata.json")) as f:
    metadata = json.load(f)
```
- Zero new dependencies.
- JSON is bounded (no code-exec surface). `numpy.load(allow_pickle=False)` is the safe default.
- Slightly more verbose than safetensors.

**Option C — Refuse to ship `load()` from disk; rebuild from authoritative source**
- If the FAISS index can always be reconstructed from the upstream embeddings DB on agent startup, `load()` may not be needed at all.
- Trades startup latency (rebuild) for security (no untrusted I/O surface).

### Verification after fix

```bash
# Sprint 6 audit tool re-run should report no HIGH findings:
bandit -r services/semantic_search -ll
# Expected: "No issues identified"
```

Add a unit test that round-trips through your chosen format and asserts:
1. Bytes saved == bytes loaded (deterministic).
2. Loading a tampered file fails fast (e.g. checksum mismatch, JSON parse error) — not silently executes.

---

## Finding 2 (advisory) — Sprint 3 dependencies need security floors

When you add Sprint 3's deps to `requirements.txt` (sentence-transformers,
faiss-cpu, qdrant-client, etc.), please run:

```bash
pip-audit
```

before merging. Sprint 6 added security floor pins to `requirements.txt` for
`urllib3`, `markdown`, `idna` (CVE closures). Your additions may pull in new
transitive deps; the audit will catch any new CVEs.

---

## Finding 3 (advisory) — Capability matrix update

When Sprint 3 deploys Qdrant + Milvus, update
`infrastructure/security/capabilities.yaml`:

```yaml
services:
  qdrant:   # already declared (Sprint 6) — confirm port + selector match your Helm chart
    selector: { app: qdrant }
    ports: [{ port: 6333, protocol: TCP }]
  milvus:
    selector: { app: milvus }
    ports: [{ port: 19530, protocol: TCP }]
```

Then re-run `python scripts/security/generate_policies.py` and commit the
regenerated `infrastructure/k3s/network-policies-per-agent.yaml` so
`scripts/security/audit_rbac.sh` keeps reporting clean.

If your Helm chart uses different label keys than `app:`, update the
selectors in `capabilities.yaml` to match before running the generator.

---

## Contact / questions

If anything in the remediation options doesn't match your design constraints,
raise it before merging. Sprint 6 is already shipping with the assumption that
no agent loads untrusted serialized data — keeping that assumption intact is
the only blocking requirement.

— Claude Code
