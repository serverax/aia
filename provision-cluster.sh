#!/bin/bash
set -e

CONTROLLER_IP="148.251.247.56"
WORKER1_IP="138.201.253.245"
WORKER2_IP="138.201.202.174"
SSH_USER="root"

echo "════════════════════════════════════════════════════"
echo "KUBERNETES CLUSTER PROVISIONING"
echo "════════════════════════════════════════════════════"
echo "Controller: $CONTROLLER_IP"
echo "Worker 1:   $WORKER1_IP"
echo "Worker 2:   $WORKER2_IP"
echo ""

# STEP 0: SSH preflight - fail fast if keys aren't set up
echo "[0/6] Preflight: verifying SSH to all hosts..."
for HOST in $CONTROLLER_IP $WORKER1_IP $WORKER2_IP; do
  ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
      $SSH_USER@$HOST 'hostname' \
    || { echo "SSH to $HOST failed - set up key-based root access first"; exit 1; }
done
echo "SSH OK on all hosts"

# STEP 1: Setup Controller
echo "[1/6] Setting up Controller Node..."
ssh $SSH_USER@$CONTROLLER_IP << 'CTRL'
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git vim htop
swapoff -a && sed -i '/ swap / s/^/#/' /etc/fstab
modprobe br_netfilter && modprobe overlay
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.bridge.bridge-nf-call-iptables=1
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.28.0 sh - --cluster-init
sleep 30
echo "Controller ready"
CTRL

# Get token
K3S_TOKEN=$(ssh $SSH_USER@$CONTROLLER_IP "cat /var/lib/rancher/k3s/server/node-token")
echo "Token obtained"

# STEP 2: Setup Workers
echo "[2/6] Setting up Worker Nodes..."
for WORKER_IP in $WORKER1_IP $WORKER2_IP; do
  echo "Worker: $WORKER_IP"
  ssh $SSH_USER@$WORKER_IP << WORK
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git vim htop
swapoff -a && sed -i '/ swap / s/^/#/' /etc/fstab
modprobe br_netfilter && modprobe overlay
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.bridge.bridge-nf-call-iptables=1
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.28.0 K3S_URL=https://$CONTROLLER_IP:6443 K3S_TOKEN=$K3S_TOKEN sh -
sleep 20
echo "Worker ready"
WORK
done

# STEP 3: Verify cluster
echo "[3/6] Verifying cluster..."
sleep 10
ssh $SSH_USER@$CONTROLLER_IP "kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml get nodes"

# STEP 4: Create namespace
echo "[4/6] Creating namespace..."
ssh $SSH_USER@$CONTROLLER_IP << 'NS'
cat << 'EOF' | kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: synthetic-enterprise
  labels:
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
    requests.cpu: "100"
    requests.memory: "200Gi"
    limits.cpu: "200"
    limits.memory: "400Gi"
    pods: "500"
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: synthetic-enterprise
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-internal
  namespace: synthetic-enterprise
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
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
      cpu: "10"
      memory: "20Gi"
    min:
      cpu: "100m"
      memory: "128Mi"
    default:
      cpu: "500m"
      memory: "512Mi"
EOF
sleep 10
echo "Namespace created"
NS

# STEP 5: Verify namespace
echo "[5/6] Verifying namespace..."
ssh $SSH_USER@$CONTROLLER_IP "kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml get all -n synthetic-enterprise && kubectl --kubeconfig=/etc/rancher/k3s/k3s.yaml describe ns synthetic-enterprise"

# STEP 6: Download kubeconfig
echo "[6/6] Finalizing..."
mkdir -p ~/.kube
scp $SSH_USER@$CONTROLLER_IP:/etc/rancher/k3s/k3s.yaml ~/.kube/aia-config.yaml
sed -i "s/127.0.0.1/$CONTROLLER_IP/g" ~/.kube/aia-config.yaml

echo ""
echo "════════════════════════════════════════════════════"
echo "KUBERNETES CLUSTER READY"
echo "════════════════════════════════════════════════════"
echo ""
echo "Cluster:"
echo "  Controller: $CONTROLLER_IP"
echo "  Workers: $WORKER1_IP, $WORKER2_IP"
echo ""
echo "Namespace: synthetic-enterprise"
echo "  CPU Quota: 100"
echo "  Memory: 200Gi"
echo "  Network policies: Enabled"
echo "  Pod limit: 500"
echo ""
echo "Use cluster:"
echo "  export KUBECONFIG=~/.kube/aia-config.yaml"
echo "  kubectl get nodes"
echo "  kubectl get all -n synthetic-enterprise"
