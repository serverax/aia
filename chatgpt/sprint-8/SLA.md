# Sprint 8 SLA Definition

## Service Targets

| Area | Target |
| --- | --- |
| Compliance Service availability | 99.95% monthly |
| Agent execution plane availability | 99.9% monthly |
| Frontend availability | 99.9% monthly |
| Audit log durability | Daily backup plus restore evidence |
| Incident acknowledgement | 15 minutes for critical incidents |
| Kill-switch activation | Under 2 minutes after human approval |
| RTO | 60 minutes |
| RPO | 15 minutes |

## Performance Targets

| Endpoint Class | Target |
| --- | --- |
| Health/readiness | p95 under 500 ms |
| Compliance policy evaluation | p95 under 1,500 ms |
| Task submission | p95 under 2,000 ms |
| UI page load | p95 under 3,000 ms |

## Error Budget

Monthly error budget is derived from the availability target for each service. Any compliance incident, audit-chain failure, or unauthorized external-send event pauses production release until reviewed by a human.

## Release Gate

Production launch requires:

- Passing load test evidence
- Passing security evidence
- Passing disaster recovery evidence
- Passing blue-green deployment evidence
- Human approval for any exception
