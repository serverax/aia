#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/mnt/f/aia}"
DEV_NS="${DEV_NS:-aia-dev}"
DEV_DOMAIN="${DEV_DOMAIN:-dev.ordinoxai.com}"
PROD_DOMAIN="${PROD_DOMAIN:-ordinoxai.com}"

echo "=================================================="
echo "Fix AIA DEV web CrashLoop safely"
echo "Project root: ${PROJECT_ROOT}"
echo "Dev namespace: ${DEV_NS}"
echo "Dev domain: ${DEV_DOMAIN}"
echo "=================================================="

cd "${PROJECT_ROOT}"

# ----------------------------------------------------------
# Patch old hardcoded /mnt/f/aia-dev root check if present
# ----------------------------------------------------------

if [ -f scripts/aia-dev-full-infra-auto.sh ]; then
  python3 - <<'PY'
from pathlib import Path

p = Path("scripts/aia-dev-full-infra-auto.sh")
text = p.read_text()

old = '''if [[ "${PROJECT_ROOT}" != "/mnt/f/aia-dev" ]]; then
  echo "ERROR: PROJECT_ROOT must be /mnt/f/aia-dev for this dev script."
  exit 1
fi'''

new = '''if [[ "${PROJECT_ROOT}" != "/mnt/f/aia" && "${PROJECT_ROOT}" != "/mnt/f/aia-dev" ]]; then
  echo "ERROR: PROJECT_ROOT must be /mnt/f/aia or /mnt/f/aia-dev for this dev script."
  exit 1
fi'''

if old in text:
    text = text.replace(old, new)
    p.write_text(text)
    print("Patched PROJECT_ROOT guard in", p)
else:
    print("PROJECT_ROOT guard already patched or not found.")
PY
fi

# ----------------------------------------------------------
# Replace broken nginx root/port 80 placeholder with unprivileged nginx
# ----------------------------------------------------------

mkdir -p generated/k8s/70-ingress

cat > generated/k8s/70-ingress/aia-dev-placeholder-web.yaml <<YAML
apiVersion: v1
kind: ConfigMap
metadata:
  name: aia-dev-placeholder-html
  namespace: ${DEV_NS}
data:
  index.html: |
    <!doctype html>
    <html>
      <head>
        <title>AIA DEV</title>
        <meta charset="utf-8" />
      </head>
      <body style="font-family: Arial, sans-serif; padding: 40px;">
        <h1>AIA Hiring Webapp DEV</h1>
        <p>Status: running</p>
        <p>Domain: ${DEV_DOMAIN}</p>
        <p>Protected production domain: ${PROD_DOMAIN}</p>
        <p>This is a dev placeholder and does not modify production DNS.</p>
      </body>
    </html>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aia-dev-web
  namespace: ${DEV_NS}
  labels:
    app: aia-dev-web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aia-dev-web
  template:
    metadata:
      labels:
        app: aia-dev-web
        environment: dev
    spec:
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.27-alpine
          ports:
            - name: http
              containerPort: 8080
          volumeMounts:
            - name: html
              mountPath: /usr/share/nginx/html
              readOnly: true
          resources:
            requests:
              cpu: "50m"
              memory: "64Mi"
            limits:
              cpu: "250m"
              memory: "256Mi"
          securityContext:
            runAsNonRoot: true
            runAsUser: 101
            runAsGroup: 101
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
      volumes:
        - name: html
          configMap:
            name: aia-dev-placeholder-html
---
apiVersion: v1
kind: Service
metadata:
  name: aia-dev-web
  namespace: ${DEV_NS}
spec:
  selector:
    app: aia-dev-web
  ports:
    - name: http
      port: 80
      targetPort: 8080
YAML

cat > generated/k8s/70-ingress/aia-dev-ingress.yaml <<YAML
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aia-dev-ingress
  namespace: ${DEV_NS}
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - ${DEV_DOMAIN}
      secretName: aia-dev-tls
  rules:
    - host: ${DEV_DOMAIN}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: aia-dev-web
                port:
                  number: 80
YAML

echo ""
echo "Safety check: root domain must not be ingress host..."
if grep -R "host: ${PROD_DOMAIN}" generated/k8s; then
  echo "ERROR: root production domain found as ingress host."
  exit 1
fi

echo ""
echo "Applying fixed DEV web and ingress only..."
kubectl apply -f generated/k8s/70-ingress/aia-dev-placeholder-web.yaml
kubectl apply -f generated/k8s/70-ingress/aia-dev-ingress.yaml

echo ""
echo "Waiting for fixed web rollout..."
kubectl -n "${DEV_NS}" rollout status deploy/aia-dev-web --timeout=180s

echo ""
echo "Current pods:"
kubectl -n "${DEV_NS}" get pods -o wide

echo ""
echo "Web logs:"
kubectl -n "${DEV_NS}" logs deploy/aia-dev-web --tail=50 || true

echo ""
echo "Service test from inside cluster:"
kubectl -n "${DEV_NS}" run aia-web-curl-test \
  --rm -i \
  --image=curlimages/curl:8.10.1 \
  --restart=Never \
  -- curl -sS http://aia-dev-web.${DEV_NS}.svc.cluster.local | head -20

echo ""
echo "Done. Web repair completed."
