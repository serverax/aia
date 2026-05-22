# Monitoring Setup Guide

## Current Status

✅ **Deployed:**
- Grafana Dashboard ConfigMap (compliance-service-dashboard)
- Incident Response Runbook

⏳ **Pending (requires Prometheus Operator CRDs):**
- ServiceMonitor (requires prometheus-operator)
- PrometheusRule (requires prometheus-operator)

## To Complete Monitoring Setup

### Option 1: Install Prometheus Operator (Recommended)

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus Operator
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set grafana.enabled=false

# Then apply the monitoring manifests
kubectl apply -f infrastructure/monitoring/prometheus-servicemonitor.yaml
kubectl apply -f infrastructure/monitoring/prometheus-rules.yaml
```

### Option 2: Use Static Prometheus Config

Skip CRDs and configure Prometheus manually:

```bash
kubectl create configmap prometheus-config --from-file=prometheus.yml -n monitoring
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: prometheus
  namespace: monitoring
spec:
  containers:
  - name: prometheus
    image: prom/prometheus:latest
    ports:
    - containerPort: 9090
    volumeMounts:
    - name: config
      mountPath: /etc/prometheus
  volumes:
  - name: config
    configMap:
      name: prometheus-config
