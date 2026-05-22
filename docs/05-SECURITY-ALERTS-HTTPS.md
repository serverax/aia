# Security, Monitoring Alerts & HTTPS

## Monitoring Dashboards

### URLs
- **Grafana:** https://grafana.ordinoxai.com
- **Prometheus:** https://prometheus.ordinoxai.com  
- **AlertManager:** https://alerts.ordinoxai.com

## Alert Notifications

### Slack Setup
1. Create webhook: https://api.slack.com/messaging/webhooks
2. Update alertmanager-config.yaml with webhook URL
3. Apply: `kubectl apply -f infrastructure/monitoring/alertmanager-config.yaml`

### Alerts
- **Critical:** Error rate >5%, Latency >1s, Replicas down
- **Warning:** Error rate 0.1-1%, Latency 200-500ms
- **Info:** Deployment updates (dashboard only)

## Security

### HTTPS
- Let's Encrypt certificates
- Auto-renewal enabled
- All dashboards use TLS

### Network Policies
- Only ingress-nginx can access
- Prometheus can scrape metrics
- Pod-to-pod communication allowed

### RBAC
- grafana-viewer role (read-only)
- Minimal permissions

### Verification
```bash
kubectl -n monitoring get networkpolicies
kubectl -n monitoring get ingress
kubectl -n monitoring get certificate
```

## Troubleshooting

### Certificate Issues
- Wait 5-10 minutes for cert-manager
- Check: `kubectl -n monitoring get certificate -w`

### No Metrics
- Check Prometheus targets: https://prometheus.ordinoxai.com/targets
- Verify ServiceMonitor: `kubectl -n synthetic-enterprise get servicemonitor`

### Network Policy Blocking
- Check policies: `kubectl -n monitoring get networkpolicies`
- Verify pod labels match selectors
