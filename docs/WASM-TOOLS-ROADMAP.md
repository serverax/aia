# WASM Tools Roadmap

Phased plan for the curated WASM tool registry. Sprint 6 builds the
infrastructure + three reference tools to prove the pattern. Real
business tools are added per agent need in Sprint 7+, following the
template established in Sprint 6.

This is intentional pacing: tools aren't bet-the-farm decisions and we
don't know yet which pure-function operations each agent will actually
call. Build the safe loading dock first; load specific cargo as agents
ask for it.

---

## Phases

### Sprint 6 (Weeks 12–13) — Infrastructure + reference tools

**Deliverable:** Tool runtime (`services/tool_sandbox/`), Cosign signing
pipeline, sigstore admission, three reference tools end-to-end.

Reference tools:
- `parse_dates_v3` — extract date ranges from text (locale-aware)
- `extract_citations_v1` — pull statutory citations from a document
- `validate_regulation_v1` — given a citation, check it exists in a known list

**Done when:** an agent can call any of the three by name from a Claude
tool-use response, get a signed `.wasm` from the registry, execute with
limits, and consume the JSON result.

### Sprint 7 (Weeks 14–15) — Business tool catalog (as inventoried)

**Deliverable:** Inventory of Sprint 3 (Gemini) and Sprint 5 (Cursor)
agent Python code to identify pure-function operations that should be
ported to WASM. Add those tools to `tools/`.

Likely candidates (to be confirmed during inventory):
- `score_severance_risk` — given case parameters, return a numeric risk
- `redact_pii` — input text → text with PII tokens replaced
- `compare_clauses` — diff two contract clauses, return structured changeset
- `format_legal_citation` — convert raw citation to OSCOLA / Bluebook format

**Out of scope for WASM (stay as direct Python calls inside the agent):**
anything that needs network (`qdrant_search`, `web_search`, `fetch_document`),
disk (`save_artifact`), or LLM calls (`summarize_with_claude`). WASM has
no network and we deliberately give the sandbox no preopened directories.

### Sprint 8 (Week 16) — Hardening pass

**Deliverable:** trivy + pen-test of the tool runtime, key rotation
verification, audit log review, capacity testing (concurrent tool calls
per agent).

---

## How to add a new tool

Once Sprint 6 ships, adding a tool is a single PR:

1. **Create the crate.** Copy `tools/parse_dates_v3/` to `tools/<your_tool>/`.
2. **Write the logic in `src/lib.rs`.** Use `tools/SDK/` for stdin/stdout JSON helpers.
3. **Define the contract in `schema.json`.** Input and output JSON Schemas (machine-readable).
4. **Fill `tool.yaml`.** Name, version, owner, allowed_agents, capability_class, description.
5. **Add a test in `services/tool_sandbox/tests/`** that loads, executes, and asserts the schema.

CI (the self-hosted runner in the K3s cluster — see DESIGN.md § D-CI) will:
- `cargo build --release --target wasm32-wasip1`
- `cosign sign-blob --key vault://... <tool>.wasm`
- push the signed `.wasm` to the artifact registry

No code changes to `services/tool_sandbox/` are needed — the registry is
data-driven, indexing on `tool.yaml`.

---

## What qualifies as a WASM tool

**Yes:**
- Pure function: same input → same output
- Bounded runtime (< 100 ms CPU)
- Bounded memory (< 64 MiB)
- No network, filesystem, or environment access needed
- Input fits in JSON; output fits in JSON

**No:**
- Anything calling an external service (Postgres, Redis, Qdrant, Milvus, HTTP APIs)
- Anything reading or writing files
- Anything that needs to spawn processes
- Anything stateful across invocations
- Anything LLM-generated at runtime (Sprint 6 is curated-registry only — see DESIGN.md § D6)

If a tool fails the "yes" criteria, it stays as a direct Python call in
the agent. It still needs an audit log entry, but it doesn't need WASM
isolation — the agent itself is the trust boundary for those calls.

---

## Acceptance criteria for adding a tool

A tool PR is merged when:

- [ ] `cargo build --release --target wasm32-wasip1` succeeds
- [ ] `schema.json` validates against draft-2020-12 JSON Schema
- [ ] `tool.yaml` parses and lists `allowed_agents` from the known agent set
- [ ] Unit test in `services/tool_sandbox/tests/` exercises happy path + at least one rejection case
- [ ] Cosign sign-blob succeeds against the staging key
- [ ] sigstore policy-controller allows the signed artifact on staging
- [ ] Integration test demonstrates the tool being called from at least one agent

---

## Tracking

Per-tool work tracked in GitHub issues with label `wasm-tool`. Roadmap
candidates above become issues as Sprint 7 starts and agent owners
confirm need.
