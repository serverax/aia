# Tools — Sprint 6 WASM Sandbox

This directory holds the source code for each curated tool the agents
may call. Every tool compiles to a single WASI command module that
reads JSON from stdin and writes JSON to stdout.

## Layout

```
tools/
├── Cargo.toml              # workspace manifest (all tools share target/)
├── sdk/                    # shared Rust helpers (json I/O, error reporting)
└── <tool_name>/
    ├── Cargo.toml
    ├── src/main.rs         # tool logic
    ├── schema.json         # input + output JSON Schema
    ├── tool.yaml           # registry metadata
    └── dist/               # populated by scripts/security/build-and-sign-tools.sh
        ├── <tool_name>.wasm
        └── <tool_name>.wasm.sig
```

## Add a new tool

See `docs/WASM-TOOLS-ROADMAP.md` for the 5-step recipe and acceptance
criteria. Short version:

1. `cp -r tools/parse_dates_v3 tools/<your_name>`
2. Replace `src/main.rs` with your logic
3. Update `schema.json` (input + output JSON Schema)
4. Update `tool.yaml` (name, version, allowed_agents)
5. Add a test in `services/tool_sandbox/tests/` exercising the new tool

## Build locally

Requires Rust 1.81+ and the `wasm32-wasip1` target:

```bash
rustup target add wasm32-wasip1
bash scripts/security/build-and-sign-tools.sh
```

CI does this on the self-hosted runner in the K3s cluster (see
`claude-code/sprint-6/DESIGN.md` § D8).
