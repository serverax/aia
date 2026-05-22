# Incident Response Runbook

## Overview

This runbook covers incident response for compliance-service blue-green deployments.

## Alert: High Error Rate (>5%)

**Severity:** CRITICAL

**Detection:** PrometheusRule `ComplianceServiceHighErrorRate`

**Investigation:**
```bash
# Check pod logs
kubectl -n synthetic-enterprise logs -l app=compliance-service --tail=50

# Check error types
kubectl -n synthetic-enterprise logs -l app=compliance-service | grep -i error

# Check current canary weight
kubectl -n synthetic-enterprise get ingress synthetic-enterprise-ingress -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}'

# Check metrics
curl -s http://prometheus:9090/api/v1/query?query=rate%28http_requests_total%7Bstatus%3D%22500%22%7D%5B5m%5D%29
```

**Resolution:**

If error rate on green (canary):
```bash
# Option 1: Reduce canary weight
kubectl -n synthetic-enterprise annotate ingress synthetic-enterprise-ingress nginx.ingress.kubernetes.io/canary-weight='0' --overwrite

# Option 2: Full rollback
bash scripts/compliance/rollback-blue-green.sh false
```

If error rate on blue:
```bash
# Scale up blue replicas
kubectl -n synthetic-enterprise scale deployment compliance-service --replicas=3
```

---

## Alert: High Latency (P99 > 1s)

**Severity:** WARNING

**Detection:** PrometheusRule `ComplianceServiceHighLatency`

**Investigation:**
```bash
# Check resource usage
kubectl -n synthetic-enterprise top pods -l app=compliance-service

# Check node status
kubectl describe nodes

# Check slow queries in logs
kubectl -n synthetic-enterprise logs -l app=compliance-service | grep -i "duration\|latency"
```

**Resolution:**

If resource constrained:
```bash
# Scale up replicas
kubectl -n synthetic-enterprise scale deployment compliance-service --replicas=4

# Increase resource limits
kubectl -n synthetic-enterprise set resources deployment compliance-service \
  --limits=cpu=1000m,memory=1Gi \
  --requests=cpu=500m,memory=512Mi
```

If canary is slower:
```bash
# Reduce canary weight to stabilize
kubectl -n synthetic-enterprise annotate ingress synthetic-enterprise-ingress nginx.ingress.kubernetes.io/canary-weight='25' --overwrite
```

---

## Alert: Canary Weight Stuck

**Severity:** WARNING

**Detection:** PrometheusRule `ComplianceServiceCanaryWeightStuck`

**Investigation:**
```bash
# Check ingress annotation
kubectl -n synthetic-enterprise get ingress synthetic-enterprise-ingress -o yaml | grep canary-weight

# Check ingress controller logs
kubectl -n ingress-nginx logs -l app.kubernetes.io/name=ingress-nginx --tail=50

# Check if annotation was applied
kubectl -n synthetic-enterprise describe ingress synthetic-enterprise-ingress
```

**Resolution:**

Manually set weight:
```bash
# Verify target weight
TARGET_WEIGHT=50

# Apply annotation
kubectl -n synthetic-enterprise annotate ingress synthetic-enterprise-ingress \
  nginx.ingress.kubernetes.io/canary-weight="$TARGET_WEIGHT" --overwrite

# Verify
kubectl -n synthetic-enterprise get ingress synthetic-enterprise-ingress -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}'
```

---

## Alert: Replicas Down

**Severity:** CRITICAL

**Detection:** PrometheusRule `ComplianceServiceReplicasDown`

**Investigation:**
```bash
# Check pod status
kubectl -n synthetic-enterprise get pods -l app=compliance-service

# Check failed pod logs
kubectl -n synthetic-enterprise logs <pod-name> --previous

# Check events
kubectl -n synthetic-enterprise describe pod <pod-name>
```

**Resolution:**

If CrashLoopBackOff:
```bash
# Check image
kubectl -n synthetic-enterprise get pods -o jsonpath='{.items[0].spec.containers[0].image}'

# Rollback deployment
kubectl -n synthetic-enterprise rollout undo deployment/compliance-service
```

If pending:
```bash
# Check node resources
kubectl describe nodes

# Scale down other workloads if needed
kubectl -n synthetic-enterprise scale deployment <other> --replicas=1
```

---

## Emergency Rollback

**When to rollback:**
- Error rate > 1% consistently
- P99 latency > 500ms
- Pod crash loop
- Database connection errors
- Any prod incident you're unsure about

**Execute rollback:**
```bash
bash scripts/compliance/rollback-blue-green.sh false
```

**Verify rollback:**
```bash
# Check weight is 0
kubectl -n synthetic-enterprise get ingress synthetic-enterprise-ingress -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}'

# Check deployment is healthy
kubectl -n synthetic-enterprise rollout status deployment/compliance-service

# Check error rate dropped
curl -s http://prometheus:9090/api/v1/query?query=rate%28http_requests_total%7Bstatus%3D%22500%22%7D%5B1m%5D%29
```

---

## Post-Incident Review

After any incident:

1. **Gather logs and metrics**
```bash
   kubectl logs -n synthetic-enterprise deployment/compliance-service > incident-logs.txt
   # Export Grafana dashboard to PDF
```

2. **Timeline**
   - When did alert fire?
   - When was incident detected?
   - When was fix applied?
   - When did metrics recover?

3. **Root cause**
   - What failed?
   - Why did monitoring not catch it earlier?
   - What changes were deployed?

4. **Action items**
   - Add more alerts?
   - Reduce alert thresholds?
   - Update runbook?
   - Add more tests?

5. **Document**
```bash
   cat > docs/incidents/incident-YYYY-MM-DD.md <<EOF
   # Incident: [Title]
   
   **Date:** YYYY-MM-DD
   **Severity:** [Critical/High/Medium]
   **Duration:** [HH:MM]
   **Impact:** [Describe impact]
   
   ## Timeline
   - HH:MM Alert fired
   - HH:MM Incident confirmed
   - HH:MM Fix deployed
   - HH:MM Resolved
   
   ## Root Cause
   [Description]
   
   ## Actions
   - [ ] Action 1
   - [ ] Action 2
   EOF
```

