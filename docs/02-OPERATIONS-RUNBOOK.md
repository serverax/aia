# Operations Runbook - v1.0

## Daily Checks

```bash
# Cluster health
kubectl get nodes
kubectl top nodes

# Compliance-service
kubectl -n synthetic-enterprise get deployment,pods,svc

# Monitoring
kubectl -n monitoring get pods

# Alerts
curl -s http://localhost:9093/api/v1/alerts | jq '.data | length'
```

## Common Operations

### Scale
```bash
kubectl -n synthetic-enterprise scale deployment compliance-service --replicas=4
```

### Update Image
```bash
kubectl -n synthetic-enterprise set image \
  deployment/compliance-service \
  compliance-service=ghcr.io/serverax/compliance-service:v2.1
```

### Restart
```bash
kubectl -n synthetic-enterprise rollout restart deployment/compliance-service
```

## Emergency

### Service Down
```bash
bash scripts/compliance/rollback-blue-green.sh false
kubectl -n synthetic-enterprise delete pods -l app=compliance-service
```

### High Memory
```bash
kubectl set resources deployment compliance-service --limits=memory=1Gi
kubectl -n synthetic-enterprise rollout restart deployment/compliance-service
```

### Disk Full
```bash
df -h
find /var/log -name "*.log" -mtime +7 -delete
```
