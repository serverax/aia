#!/bin/bash
# DEPRECATED: This script assumes Ubuntu/Debian nodes with SSH access.
# Talos is API-managed (no SSH, no package manager, no runtime K3s install).
#
# For Talos provisioning, use:
#   talosctl gen config
#   talosctl apply-config -n <node-ip>
#
# See: https://docs.talos.dev/latest/learn-more/what-is-talos/
#
# If you're not using Talos, this script may still apply to other Linux clusters.
# If you hit this message by accident and need K3s provisioning, contact ops.

echo "ERROR: provision-cluster-full.sh is deprecated for Talos clusters." >&2
echo "See header comments for alternatives." >&2
exit 1

set -e

CONTROLLER_IP="148.251.247.56"
WORKER1_IP="138.201.253.245"
WORKER2_IP="138.201.202.174"
SSH_USER="root"
SECRETS_DIR="$HOME/.aia"
SECRETS_FILE="$SECRETS_DIR/secrets"
KUBECONFIG_PATH="$HOME/.kube/aia-config.yaml"

echo "════════════════════════════════════════════════════"
echo "FULL K3S + STACK PROVISIONING"
echo "════════════════════════════════════════════════════"
echo "Controller: $CONTROLLER_IP"
echo "Workers:    $WORKER1_IP, $WORKER2_IP"
echo ""

# ──────────────────────────────────────────────────────
# STEP 0a: SSH preflight - fail fast if keys aren't set up
# ──────────────────────────────────────────────────────
echo "[0/10] SSH preflight..."
for HOST in $CONTROLLER_IP $WORKER1_IP $WORKER2_IP; do
  ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
      $SSH_USER@$HOST 'hostname' \
    || { echo "SSH to $HOST failed - set up key-based root access first"; exit 1; }
done
echo "SSH OK"

# ──────────────────────────────────────────────────────
# STEP 0b: Generate secrets ONCE and persist
# ──────────────────────────────────────────────────────
echo "[0/10] Secrets..."
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"
if [ ! -f "$SECRETS_FILE" ]; then
  PG_PASS=$(openssl rand -base64 32 | tr -d '=+/' | head -c 32)
  REDIS_PASS=$(openssl rand -base64 32 | tr -d '=+/' | head -c 32)
  GRAFANA_PASS=$(openssl rand -base64 32 | tr -d '=+/' | head -c 32)
  cat > "$SECRETS_FILE" << SECRETS
PG_PASS=$PG_PASS
REDIS_PASS=$REDIS_PASS
GRAFANA_PASS=$GRAFANA_PASS
SECRETS
  chmod 600 "$SECRETS_FILE"
  echo "Saved $SECRETS_FILE"
else
  echo "Reusing $SECRETS_FILE"
  set -a; source "$SECRETS_FILE"; set +a
fi

# ──────────────────────────────────────────────────────
# STEP 1: Controller (K3s server, embedded etcd)
# ──────────────────────────────────────────────────────
echo "[1/10] Controller K3s..."
ssh $SSH_USER@$CONTROLLER_IP 'bash -s' << 'CTRL'
set -e
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git vim htop net-tools nfs-common
swapoff -a && sed -i '/ swap / s/^/#/' /etc/fstab
modprobe br_netfilter && modprobe overlay
cat > /etc/sysctl.d/k3s.conf << SYSCTL
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
fs.inotify.max_user_watches = 2097152
vm.overcommit_memory = 1
SYSCTL
sysctl -p /etc/sysctl.d/k3s.conf
if ! command -v k3s >/dev/null 2>&1; then
  curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.28.0 sh - \
    --cluster-init \
    --flannel-backend=wireguard-native \
    --disable=traefik \
    --disable=servicelb \
    --write-kubeconfig-mode 644
  sleep 30
fi
cat /var/lib/rancher/k3s/server/node-token > /tmp/k3s-token.txt
CTRL

TOKEN=$(ssh $SSH_USER@$CONTROLLER_IP "cat /tmp/k3s-token.txt")
[ -n "$TOKEN" ] || { echo "FAILED: empty K3s token"; exit 1; }

# ──────────────────────────────────────────────────────
# STEP 2: Workers
# ──────────────────────────────────────────────────────
for WORKER_IP in $WORKER1_IP $WORKER2_IP; do
  echo "[2/10] Worker $WORKER_IP..."
  ssh $SSH_USER@$WORKER_IP "bash -s" << WORKER
set -e
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git vim htop net-tools nfs-common
swapoff -a && sed -i '/ swap / s/^/#/' /etc/fstab
modprobe br_netfilter && modprobe overlay
cat > /etc/sysctl.d/k3s.conf << SYSCTL
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
fs.inotify.max_user_watches = 2097152
SYSCTL
sysctl -p /etc/sysctl.d/k3s.conf
if ! command -v k3s >/dev/null 2>&1; then
  curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.28.0 \
    K3S_URL=https://$CONTROLLER_IP:6443 K3S_TOKEN=$TOKEN sh -
  sleep 20
fi
WORKER
done

# ──────────────────────────────────────────────────────
# STEP 3: Local kubeconfig
# ──────────────────────────────────────────────────────
echo "[3/10] Kubeconfig..."
mkdir -p "$(dirname "$KUBECONFIG_PATH")"
scp $SSH_USER@$CONTROLLER_IP:/etc/rancher/k3s/k3s.yaml "$KUBECONFIG_PATH"
sed -i "s/127.0.0.1/$CONTROLLER_IP/g" "$KUBECONFIG_PATH"
chmod 600 "$KUBECONFIG_PATH"
export KUBECONFIG="$KUBECONFIG_PATH"
sleep 15
kubectl wait --for=condition=Ready node --all --timeout=300s || true

# ──────────────────────────────────────────────────────
# STEP 4: Helm + repos
# ──────────────────────────────────────────────────────
echo "[4/10] Helm + repos..."
command -v helm >/dev/null 2>&1 \
  || curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm repo add jetstack             https://charts.jetstack.io                          || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts  || true
helm repo add grafana              https://grafana.github.io/helm-charts               || true
helm repo add bitnami              https://charts.bitnami.com/bitnami                  || true
helm repo add qdrant               https://qdrant.github.io/qdrant-helm                || true
helm repo add milvus               https://milvus-io.github.io/milvus-helm/            || true
helm repo add ingress-nginx        https://kubernetes.github.io/ingress-nginx          || true
helm repo add hashicorp            https://helm.releases.hashicorp.com                 || true
helm repo add argocd               https://argoproj.github.io/argo-helm                || true
helm repo update

# ──────────────────────────────────────────────────────
# STEP 5: Storage classes + ingress + cert-manager
# ──────────────────────────────────────────────────────
echo "[5/10] Storage + ingress..."
kubectl apply -f - << 'STORAGE'
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
STORAGE

helm upgrade --install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=30080 \
  --set controller.service.nodePorts.https=30443 \
  --wait --timeout 10m \
  || { echo "FAILED: nginx-ingress"; exit 1; }

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true --wait --timeout 10m \
  || { echo "FAILED: cert-manager"; exit 1; }

# ──────────────────────────────────────────────────────
# STEP 6: Databases
# ──────────────────────────────────────────────────────
echo "[6/10] Databases..."
kubectl create namespace databases 2>/dev/null || true
kubectl label namespace databases name=databases --overwrite

helm upgrade --install postgresql bitnami/postgresql --namespace databases \
  --set auth.username=synthetic --set auth.password="$PG_PASS" --set auth.database=synthetic_db \
  --set primary.persistence.size=100Gi \
  --wait --timeout 15m \
  || { echo "FAILED: postgresql"; exit 1; }

helm upgrade --install redis bitnami/redis --namespace databases \
  --set auth.password="$REDIS_PASS" \
  --set master.persistence.size=50Gi --set replica.replicaCount=2 \
  --wait --timeout 10m \
  || { echo "FAILED: redis"; exit 1; }

helm upgrade --install qdrant qdrant/qdrant --namespace databases \
  --set persistence.size=50Gi --wait --timeout 10m \
  || { echo "FAILED: qdrant"; exit 1; }

helm upgrade --install milvus milvus/milvus --namespace databases \
  --set persistence.enabled=true --set persistence.size=50Gi \
  --wait --timeout 20m \
  || { echo "FAILED: milvus"; exit 1; }

# ──────────────────────────────────────────────────────
# STEP 7: Monitoring + logging + jaeger
# ──────────────────────────────────────────────────────
echo "[7/10] Monitoring + logging..."
kubectl create namespace monitoring 2>/dev/null || true
kubectl label namespace monitoring name=monitoring --overwrite

helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.retention=30d \
  --set grafana.adminPassword="$GRAFANA_PASS" \
  --wait --timeout 15m \
  || { echo "FAILED: prometheus"; exit 1; }

kubectl create namespace logging 2>/dev/null || true
kubectl label namespace logging name=logging --overwrite

helm upgrade --install elasticsearch bitnami/elasticsearch --namespace logging \
  --set master.replicaCount=3 --set persistence.enabled=true \
  --wait --timeout 15m \
  || { echo "FAILED: elasticsearch"; exit 1; }

helm upgrade --install kibana bitnami/kibana --namespace logging \
  --set elasticsearch.hosts[0]=elasticsearch-coordinating --set elasticsearch.port=9200 \
  --wait --timeout 10m \
  || { echo "FAILED: kibana"; exit 1; }

kubectl apply -n monitoring -f - << 'JAEGER'
apiVersion: v1
kind: Service
metadata:
  name: jaeger
spec:
  ports:
  - port: 16686
    name: web
  - port: 6831
    name: agent
    protocol: UDP
  selector:
    app: jaeger
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:1.50
        ports:
        - containerPort: 16686
        - containerPort: 6831
          protocol: UDP
JAEGER

# ──────────────────────────────────────────────────────
# STEP 8: Vault + synthetic-enterprise namespace/RBAC/secrets
# ──────────────────────────────────────────────────────
echo "[8/10] Vault + synthetic-enterprise namespace..."
kubectl create namespace security 2>/dev/null || true
kubectl label namespace security name=security --overwrite

helm upgrade --install vault hashicorp/vault --namespace security \
  --set server.dataStorage.size=20Gi \
  --wait --timeout 10m \
  || { echo "FAILED: vault"; exit 1; }

# Heredoc is UNQUOTED so $PG_PASS / $REDIS_PASS get expanded into Secret stringData.
kubectl apply -f - << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: synthetic-enterprise
  labels:
    name: synthetic-enterprise
    app: synthetic-enterprise
    environment: production
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: synthetic-enterprise-quota
  namespace: synthetic-enterprise
spec:
  hard:
    requests.cpu: "200"
    requests.memory: "400Gi"
    limits.cpu: "400"
    limits.memory: "800Gi"
    pods: "1000"
    services: "200"
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: synthetic-enterprise
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internal
  namespace: synthetic-enterprise
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: synthetic-enterprise
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: synthetic-enterprise
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - namespaceSelector:
        matchLabels:
          name: databases
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: v1
kind: LimitRange
metadata:
  name: synthetic-enterprise-limits
  namespace: synthetic-enterprise
spec:
  limits:
  - type: Container
    max:
      cpu: "20"
      memory: "40Gi"
    min:
      cpu: "100m"
      memory: "128Mi"
    default:
      cpu: "500m"
      memory: "512Mi"
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agent-sa
  namespace: synthetic-enterprise
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: agent-role
  namespace: synthetic-enterprise
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: agent-rolebinding
  namespace: synthetic-enterprise
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: agent-role
subjects:
- kind: ServiceAccount
  name: agent-sa
  namespace: synthetic-enterprise
---
apiVersion: v1
kind: Secret
metadata:
  name: synthetic-db-credentials
  namespace: synthetic-enterprise
type: Opaque
stringData:
  db-host: postgresql.databases.svc.cluster.local
  db-port: "5432"
  db-user: synthetic
  db-name: synthetic_db
  db-password: "$PG_PASS"
---
apiVersion: v1
kind: Secret
metadata:
  name: synthetic-redis-credentials
  namespace: synthetic-enterprise
type: Opaque
stringData:
  redis-host: redis-master.databases.svc.cluster.local
  redis-port: "6379"
  redis-password: "$REDIS_PASS"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: synthetic-config
  namespace: synthetic-enterprise
data:
  ENVIRONMENT: production
  LOG_LEVEL: info
  JAEGER_ENABLED: "true"
  JAEGER_AGENT_HOST: jaeger.monitoring.svc.cluster.local
  JAEGER_AGENT_PORT: "6831"
EOF

# ──────────────────────────────────────────────────────
# STEP 9: ArgoCD + Filebeat
# ──────────────────────────────────────────────────────
echo "[9/10] ArgoCD + Filebeat..."
helm upgrade --install argocd argocd/argo-cd --namespace argocd --create-namespace \
  --set server.service.type=NodePort --set server.service.nodePort=30081 \
  --wait --timeout 15m \
  || { echo "FAILED: argocd"; exit 1; }

kubectl apply -n logging -f - << 'FILEBEAT'
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/*.log
    output.elasticsearch:
      hosts: ["elasticsearch-coordinating:9200"]
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
spec:
  selector:
    matchLabels:
      app: filebeat
  template:
    metadata:
      labels:
        app: filebeat
    spec:
      containers:
      - name: filebeat
        image: docker.elastic.co/beats/filebeat:7.17.0
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        volumeMounts:
        - name: config
          mountPath: /usr/share/filebeat/filebeat.yml
          subPath: filebeat.yml
        - name: varlog
          mountPath: /var/log
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: filebeat-config
      - name: varlog
        hostPath:
          path: /var/log
FILEBEAT

# ──────────────────────────────────────────────────────
# STEP 10: Verify
# ──────────────────────────────────────────────────────
echo "[10/10] Verify..."
sleep 30
echo ""; echo "── Nodes ──"
kubectl get nodes -o wide
echo ""; echo "── Namespaces ──"
kubectl get namespaces --show-labels
echo ""; echo "── synthetic-enterprise ──"
kubectl get all -n synthetic-enterprise
echo ""; echo "── Not-running pods ──"
kubectl get pods -A --no-headers | awk '$4!="Running" && $4!="Completed"' || true

echo ""
echo "════════════════════════════════════════════════════"
echo "DONE"
echo "════════════════════════════════════════════════════"
echo "KUBECONFIG: $KUBECONFIG_PATH"
echo "Secrets:    $SECRETS_FILE"
echo ""
echo "Vault still needs init+unseal:"
echo "  kubectl exec -n security -ti vault-0 -- vault operator init"
echo "  (save the unseal keys, then 'vault operator unseal' 3 times)"
