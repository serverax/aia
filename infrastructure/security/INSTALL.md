# Sprint 6 cluster installs

Run these AFTER `provision-cluster-full.sh` and the Vault preflight
(`infrastructure/vault/PREFLIGHT-UNSEAL.md`). Order matters.

## 1. Build the custom GHA runner image

The runner needs `cargo`, `cosign`, and the `vault` CLI baked in so each
job doesn't reinstall them.

```bash
docker build -t ghcr.io/serverax/aia/wasm-runner:latest \
    -f infrastructure/security/runner-image/Dockerfile \
    infrastructure/security/runner-image
docker push ghcr.io/serverax/aia/wasm-runner:latest
```

## 2. Install actions-runner-controller (ARC scale sets)

```bash
# Controller (cluster-wide, one install)
helm install arc \
    --namespace arc-system --create-namespace \
    oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
    --version 0.9.3

# Scale set targeting this repo
kubectl create namespace arc-runners
kubectl create secret generic github-pat \
    -n arc-runners \
    --from-literal=github_token="${GH_RUNNER_PAT}"   # PAT with repo + workflow scopes

helm install aia-runners \
    --namespace arc-runners \
    -f infrastructure/security/runner-scale-set.yaml \
    oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
    --version 0.9.3
```

CI workflows reference this scale set with:

```yaml
jobs:
  build-tools:
    runs-on: aia-runners       # matches helm release name
```

## 3. Install sigstore policy-controller

```bash
helm repo add sigstore https://sigstore.github.io/helm-charts
helm repo update

helm install policy-controller sigstore/policy-controller \
    --namespace cosign-system --create-namespace \
    --version 0.10.2
```

Push the Vault-issued Cosign public key into a ConfigMap so the policy
can reference it:

```bash
vault read -format=json cosign/cert/aia-cosign \
    | jq -r '.data.public_key' \
    > /tmp/aia-cosign.pub

kubectl create configmap aia-cosign-pubkey \
    -n cosign-system \
    --from-file=cosign.pub=/tmp/aia-cosign.pub

kubectl apply -f infrastructure/security/cluster-image-policy.yaml
```

Verify enforcement with the test in `tests/security/test_admission_rejects_unsigned.py`.

## 4. Install Kyverno + hardening policies

```bash
helm repo add kyverno https://kyverno.github.io/kyverno
helm repo update

helm install kyverno kyverno/kyverno \
    --namespace kyverno --create-namespace \
    --version 3.2.6

# Wait for webhooks to be ready, then apply policies
kubectl wait -n kyverno --for=condition=ready pod -l app.kubernetes.io/instance=kyverno --timeout=2m
kubectl apply -f infrastructure/security/kyverno-policies.yaml
```

## Verification

```bash
# All three controllers up?
kubectl -n arc-system get pods
kubectl -n cosign-system get pods
kubectl -n kyverno get pods

# Scale set registered with GitHub?
kubectl -n arc-runners get autoscalingrunnersets.actions.github.com

# Image policy + Kyverno policies present?
kubectl get clusterimagepolicy
kubectl get clusterpolicy
```

When all four return healthy state, Sprint 6 Day 5 (rebuild + sign agent
images, deploy via verified path) can start.
