# Production Readiness Checklist

## Compliance

- [ ] Sprint 7 approved on real cluster
- [ ] Kill-switch API reachable from authorized operators
- [ ] External-send capability can be frozen and unfrozen by policy
- [ ] Compliance audit table exists
- [ ] Audit hash-chain verification passes
- [ ] Human override process documented

## Load

- [ ] 1,000+ concurrent user test completed
- [ ] p95 read endpoint latency below 500 ms
- [ ] p95 policy evaluation latency below 1,500 ms
- [ ] Error rate below 0.1%
- [ ] No sustained pod restarts during test

## Security

- [ ] OWASP ZAP baseline completed
- [ ] No unapproved critical findings
- [ ] No unapproved high findings
- [ ] Network policies restrict database access
- [ ] Containers run as non-root users
- [ ] Secrets are not stored in ConfigMaps

## Disaster Recovery

- [ ] Backup restore drill completed
- [ ] RTO measured at or below 60 minutes
- [ ] RPO measured at or below 15 minutes
- [ ] Audit chain verifies after restore
- [ ] Redis runtime state rehydration tested

## Deployment

- [ ] Blue deployment healthy
- [ ] Green deployment healthy
- [ ] Traffic switch validated
- [ ] Rollback validated
- [ ] Release evidence attached
- [ ] Human production approval recorded
