# Secret Inventory & Scrub Runbook (STAGED — DO NOT RUN WITHOUT AUTHORIZATION)

> Status: **prepared for human review**. No history was rewritten and no
> credentials were rotated in producing this document. Every destructive
> command below requires (a) explicit owner authorization and (b) a person
> with cluster-admin / git-admin rights. Sequencing matters — read §3 first.

## 1. Inventory (as found on 2026-05-26)

### 1a. Untracked — never committed → just delete from disk + gitignore (NO history rewrite)
| File | Contents | Action |
|---|---|---|
| `aia-developer-kubeconfig.yaml` | live K8s SA token + CA + API server `148.251.247.56:6443` | rotate SA token on cluster, delete file, gitignore |
| `generated/secrets.dev.env` | MinIO dev credentials | rotate, delete file, gitignore |

These are **not in git history**, so they need no scrub — but the *credentials
inside them are still live* and must be rotated regardless.

### 1b. Committed → require history rewrite **and** rotation
| File | Secret | Introduced in | Severity |
|---|---|---|---|
| `infrastructure/talos/gen/controlplane.yaml` | Talos machine config — appears to hold cluster CA + bootstrap/secrets | `941f27f` | 🔴 **CRITICAL** (cluster root-of-trust) |
| `infrastructure/talos/gen/worker.yaml` | Talos join token / PKI | `941f27f` | 🔴 CRITICAL |
| `openclaw-dev-working.yaml` | `dev-token-12345` | `23ffd82` | 🟡 HIGH |
| `generated/k8s/10-storage/minio-dev.yaml` | MinIO root password | `24dfc73` | 🟡 HIGH |
| `scripts/aia-dev-full-infra-auto.sh` | embedded token-like strings | `24dfc73` | 🟠 review |

Reproduce the inventory at any time (read-only):
```bash
git grep -lI -e "dev-token-12345" -e "BEGIN CERTIFICATE" -e "token:" \
  -e "MINIO_ROOT_PASSWORD" -e "client-key-data" -- . ':!*.md'
```

## 2. The two myths from the original plan (corrected)

- **`kubectl create secret … --from-literal=kubeconfig=$(kubectl config view --raw)` does NOT rotate anything.** It copies your *current* credentials into a Secret; the leaked token stays valid. Real rotation = invalidate the old credential at its source (delete/recreate the ServiceAccount token; re-key Talos PKI; reset MinIO root creds).
- **Do NOT `git push --force --all` before integrating branches.** Rewriting history changes every SHA; force-pushing rewritten branches and *then* merging multiplies conflicts and can orphan work. **Scrub history AFTER integration is merged**, on a coordinated cutover.

## 3. Correct sequence (do in this order)

**Step 0 — Rotate live credentials FIRST (cluster-admin).** The secrets are
already exposed; rotation is the only thing that actually reduces risk, and it
is independent of git. Priority order:
1. **Talos PKI** (controlplane/worker) — most severe. Rotating the cluster CA
   typically means re-keying / re-bootstrapping; if full re-key is infeasible
   short-term, at minimum rotate join tokens and treat the cluster as
   compromised-pending-rebuild. Decision needed from infra owner.
2. **`aia-developer` ServiceAccount token** — delete & recreate the token
   secret; redistribute new kubeconfig out-of-band.
3. **MinIO root creds** and **`dev-token-12345`** — reset at source.

**Step 1 — Land integration** (already prepared on local `feature/system-integration`; merge via reviewed PR per `INTEGRATION_FINDINGS.md`).

**Step 2 — Scrub history (git-admin, coordinated freeze).** Prefer
`git filter-repo` (BFG’s maintained successor). Work on a **fresh mirror**:
```bash
git clone --mirror git@github.com:serverax/aia.git aia-mirror.git
cd aia-mirror.git

# (a) remove whole-file secrets by path
git filter-repo --invert-paths \
  --path infrastructure/talos/gen/controlplane.yaml \
  --path infrastructure/talos/gen/worker.yaml \
  --path openclaw-dev-working.yaml \
  --path generated/k8s/10-storage/minio-dev.yaml \
  --path aia-developer-kubeconfig.yaml \
  --path generated/secrets.dev.env

# (b) redact literal token strings that survive in scripts/docs
git filter-repo --replace-text ../docs/integration/bfg-replacements.txt
```
(BFG alternative, if preferred: `bfg --delete-files '{controlplane.yaml,worker.yaml,openclaw-dev-working.yaml,minio-dev.yaml}'` then `bfg --replace-text bfg-replacements.txt`.)

**Step 3 — Cutover.** Coordinate a freeze (all branches pushed/merged), then
`git push --force --mirror`. Every contributor must re-clone. Anything that
isn't in `origin/main` at freeze time and isn't on the integration branch will
be lost — verify the branch list first.

**Step 4 — Prevent recurrence.** Confirm `.gitignore` covers the patterns
(see `chore/clean-artifacts`), add a pre-commit secret scanner (gitleaks /
trufflehog) to CI, and move real secrets to Sealed Secrets / External Secrets /
Vault. Talos `gen/` output should never be committed.

## 4. What was NOT done here
- ❌ No credentials rotated.  ❌ No history rewritten.  ❌ No force-push.
- ❌ Nothing applied to the cluster.
All of the above are gated on owner authorization + the right human operator.
