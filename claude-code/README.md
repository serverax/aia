# CLAUDE CODE - Sprints 1, 2, & 6: Infrastructure, Orchestration, Security

## Assignment
**Sprint 1: Weeks 1-2** - Infrastructure & Echo Agent
- K3s Cluster Setup
- PostgreSQL Database
- Redis Cache
- Jaeger Tracing
- Echo Agent Service

**Sprint 2: Weeks 3-4** - Orchestrator Agent
- Message Routing
- Redis Streams
- Load Balancing
- Service Discovery
- Metrics Export

**Sprint 6: Weeks 12-13** - Security Hardening
- WASM Sandbox
- Cosign Code Signing
- Capability-Based Security
- Runtime Isolation
- Security Audit

## Structure
```
claude-code/
â”œâ”€â”€ sprint-1/          # Infrastructure
â”œâ”€â”€ sprint-2/          # Orchestrator
â”œâ”€â”€ sprint-6/          # Security
â”œâ”€â”€ infrastructure/    # K3s deployment scripts
â”œâ”€â”€ services/          # Agent implementations
â”œâ”€â”€ security/          # Security policies
â””â”€â”€ SPRINTS-1-2-6-INSTRUCTIONS.md
```

## Quick Start
1. Read: `SPRINTS-1-2-6-INSTRUCTIONS.md`
2. Deploy K3s cluster (3 servers)
3. Deploy databases (PostgreSQL, Redis)
4. Deploy Echo Agent
5. Deploy Orchestrator Agent
6. Apply WASM security layer

## Key Technologies
- Kubernetes (K3s)
- PostgreSQL
- Redis
- FastAPI
- WasmEdge
- Cosign

## Servers
- Controller: 148.251.247.56
- Worker 1: 138.201.253.245
- Worker 2: 138.201.202.174

## Status
ðŸš€ READY TO START IMMEDIATELY

---
**Start Date**: Week 1
**End Date**: Weeks 1-2, 3-4, 12-13
**Owner**: Claude Code
