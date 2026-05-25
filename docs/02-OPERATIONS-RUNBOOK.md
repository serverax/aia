# Operations Runbook - v1.0

## Daily Checks

```bash
# Cluster health
kubectl get nodes
kubectl top nodes

# Compliance-service
kubectl -n ordinox-ai get deployment,pods,svc

# Monitoring
kubectl -n monitoring get pods

# Alerts
curl -s http://localhost:9093/api/v1/alerts | jq '.data | length'
```

## Common Operations

### Scale
```bash
kubectl -n ordinox-ai scale deployment compliance-service --replicas=4
```

### Update Image
```bash
kubectl -n ordinox-ai set image \
  deployment/compliance-service \
  compliance-service=ghcr.io/serverax/compliance-service:v2.1
```

### Restart
```bash
kubectl -n ordinox-ai rollout restart deployment/compliance-service
```

## Emergency

### Service Down
```bash
bash scripts/compliance/rollback-blue-green.sh false
kubectl -n ordinox-ai delete pods -l app=compliance-service
```

### High Memory
```bash
kubectl set resources deployment compliance-service --limits=memory=1Gi
kubectl -n ordinox-ai rollout restart deployment/compliance-service
```

### Disk Full
```bash
df -h
find /var/log -name "*.log" -mtime +7 -delete
```
