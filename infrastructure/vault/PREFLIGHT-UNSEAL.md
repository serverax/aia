# Vault Preflight — Init + Unseal (one-time, before Sprint 6 Day 1)

Sprint 6 assumes Vault is **initialized, unsealed, and reachable** at
`https://vault.vault.svc.cluster.local:8200` from inside the cluster.
This document is the runbook you (the user) follow once, after
`provision-cluster-full.sh` completes, to put Vault in that state.

**Auto-unseal is deliberately out of scope for Sprint 6** — see DESIGN.md
§ Decisions D2/D7 rationale. Auto-unseal evaluation is deferred to Sprint 8
hardening when cloud KMS options (or Transit-engine-on-Vault patterns) can
be scoped properly.

---

## Preconditions

```bash
export KUBECONFIG=~/.kube/aia-config.yaml

# 1. Cluster reachable
kubectl get nodes -o wide

# 2. Vault Helm release installed (provision-cluster-full.sh does this)
kubectl get pods -n vault -l app.kubernetes.io/name=vault
# Expect: vault-0 ... 1/1 Running (status will say "sealed" until init)

# 3. Vault HTTP API reachable
kubectl port-forward -n vault svc/vault 8200:8200 &
export VAULT_ADDR=http://localhost:8200
vault status
# Expect: Initialized: false, Sealed: true
```

---

## Step 1 — Initialize

```bash
mkdir -p ~/.aia/secrets
chmod 700 ~/.aia/secrets

vault operator init \
    -key-shares=5 \
    -key-threshold=3 \
    -format=json \
    > ~/.aia/secrets/vault-init.json

chmod 600 ~/.aia/secrets/vault-init.json
```

The JSON file contains:
- `unseal_keys_b64[0..4]` — five Shamir shares; **any three** unseal a sealed Vault
- `root_token` — full-power token, used only for the initial PKI/Transit setup on Sprint 6 Day 4, then revoked

**This file is the only copy of these secrets. Lose it and the Vault data is unrecoverable.**

Recommended:
1. Keep the JSON file at `~/.aia/secrets/vault-init.json` (chmod 600).
2. Optionally split: store unseal keys 1–3 with you, 4 with another operator, 5 in a sealed envelope.
3. Add `~/.aia/` to your existing backup routine.

---

## Step 2 — Unseal

```bash
# Run three times with three different keys from vault-init.json
vault operator unseal $(jq -r '.unseal_keys_b64[0]' ~/.aia/secrets/vault-init.json)
vault operator unseal $(jq -r '.unseal_keys_b64[1]' ~/.aia/secrets/vault-init.json)
vault operator unseal $(jq -r '.unseal_keys_b64[2]' ~/.aia/secrets/vault-init.json)

vault status
# Expect: Sealed: false, Initialized: true
```

---

## Step 3 — Verify Sprint 6 access path

```bash
export VAULT_TOKEN=$(jq -r '.root_token' ~/.aia/secrets/vault-init.json)

vault token lookup           # should return token metadata
vault secrets list           # should show default engines

# Sanity check the path Sprint 6 Day 4 will use:
vault secrets enable -path=cosign pki && vault secrets disable cosign
vault secrets enable -path=transit transit && vault secrets disable transit
# (Both should succeed and then disable cleanly — confirms write capability.)
```

If all three commands return clean, you're ready for Sprint 6 Day 1.

---

## What happens on Vault pod restart

The Vault StatefulSet pod re-seals on any restart (Shamir model). You'll
see `Sealed: true` and Sprint 6 services that touch Vault will start
failing. Recovery:

```bash
export KUBECONFIG=~/.kube/aia-config.yaml
kubectl port-forward -n vault svc/vault 8200:8200 &
export VAULT_ADDR=http://localhost:8200

# Same three unseal commands as Step 2
vault operator unseal $(jq -r '.unseal_keys_b64[0]' ~/.aia/secrets/vault-init.json)
vault operator unseal $(jq -r '.unseal_keys_b64[1]' ~/.aia/secrets/vault-init.json)
vault operator unseal $(jq -r '.unseal_keys_b64[2]' ~/.aia/secrets/vault-init.json)
```

In Sprint 8 hardening, this is what gets automated (cloud KMS or Transit-on-Vault).
For now, it's a 30-second manual op the operator runs on restart.

---

## Post Sprint 6 Day 4 — rotate the root token

Once Sprint 6 has set up the Cosign PKI mount, the root token is
**revoked** and an app-scoped token is issued:

```bash
# (Sprint 6 Day 4 code does this; documented here for reference)
vault token create \
    -policy=aia-cosign-signer \
    -ttl=720h \
    -orphan \
    > ~/.aia/secrets/vault-cosign-token.json

# Now revoke the root token:
vault token revoke $(jq -r '.root_token' ~/.aia/secrets/vault-init.json)
```

After this, only the scoped token is usable; the root token in
`vault-init.json` is dead. Keep the unseal keys — they're still needed
for re-seal recovery.
