#!/bin/bash
set -e

echo "📦 Creating compliance-service Flux manifests..."

mkdir -p clusters/ordinox-ai
mkdir -p infrastructure/compliance

cat > clusters/ordinox-ai/compliance.yaml <<'YAML'
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: compliance-service
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: flux-system
    namespace: flux-system
  path: ./infrastructure/compliance
  prune: true
  wait: true
  timeout: 5m
YAML

echo "✅ Created: clusters/ordinox-ai/compliance.yaml"

cat > infrastructure/compliance/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: ordinox-ai
resources:
  - compliance-service-deployment.yaml
  - compliance-service-svc.yaml
  - blue-green-traffic-split.yaml
YAML

echo "✅ Created: infrastructure/compliance/kustomization.yaml"

cat > infrastructure/compliance/compliance-service-deployment.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-service
  namespace: ordinox-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compliance-service
      version: v1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: compliance-service
        version: v1
    spec:
      containers:
      - name: compliance-service
        image: ghcr.io/serverax/compliance-service:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
YAML

echo "✅ Created: infrastructure/compliance/compliance-service-deployment.yaml"

cat > infrastructure/compliance/compliance-service-svc.yaml <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: compliance-service
  namespace: ordinox-ai
  labels:
    app: compliance-service
spec:
  type: ClusterIP
  selector:
    app: compliance-service
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
YAML

echo "✅ Created: infrastructure/compliance/compliance-service-svc.yaml"

git add clusters/ordinox-ai/compliance.yaml infrastructure/compliance/kustomization.yaml infrastructure/compliance/compliance-service-deployment.yaml infrastructure/compliance/compliance-service-svc.yaml

git commit -m "feat(compliance): wire compliance-service Kustomization to Flux"

git push origin main

flux reconcile source git flux-system -n flux-system
flux reconcile kustomization flux-system -n flux-system

sleep 5

echo ""
echo "📊 Checking Kustomization status..."
kubectl -n flux-system get kustomization -o wide

echo ""
echo "🔍 Checking deployment status..."
if kubectl -n ordinox-ai get deployment compliance-service &>/dev/null; then
  kubectl -n ordinox-ai rollout status deployment/compliance-service --timeout=120s
else
  echo "⚠️  Deployment pending. Checking again in 10s..."
  sleep 10
  kubectl -n ordinox-ai rollout status deployment/compliance-service --timeout=120s
fi

echo ""
echo "✅ Final status:"
kubectl -n ordinox-ai get deploy,pods,svc,endpoints -o wide

echo "🎉 Compliance-service Flux setup complete!"
