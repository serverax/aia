# Compliance Service

Sprint 7 implementation for compliance controls and containment.

## Scope

- Kill-switch API
- Compliance middleware
- Tamper-evident audit hash-chain helpers
- Kubernetes deployment policy artifacts under `infrastructure/compliance`

## Cluster Requirement

Sprint 7 acceptance requires the real Week 14-15 deployed cluster:

- K3s operational
- Echo, Orchestrator, Analyst, Frontend, and Editor deployed
- databases running
- production networking and policies active

Local tests cover deterministic policy logic only. They do not replace cluster acceptance.
