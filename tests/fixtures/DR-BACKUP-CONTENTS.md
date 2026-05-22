# DR Backup Fixture Contents

Fixture archive:

```text
tests/fixtures/sample-dr-backup.tar.gz
```

This fixture is a deterministic Sprint 8 disaster-recovery sample for the
`ordinox-ai` namespace on the `ordinox-talos-ha` cluster. It is designed for
restore script validation, audit-chain verification, and evidence capture. It
does not contain live credentials or client data.

## Archive Layout

```text
dr-backup/
  backup-manifest.json
  audit-backup.sql.gz
  secrets-backup.json
  checksums.sha256
  pvc/
    redis/
      appendonly.aof
    qdrant/
      collections.json
```

## File Inventory

### `backup-manifest.json`

Purpose: Top-level backup metadata and restore expectations.

Contains:

- backup timestamp: `2026-05-21T10:00:00Z`
- cluster: `ordinox-talos-ha`
- Kubernetes version: `v1.36.0`
- Talos version: `v1.13.2`
- namespace: `ordinox-ai`
- resource count: `15`
- resource breakdown for pods, PVCs, secrets, configmaps, services, deployments,
  network policies, ingress, service accounts, and limit ranges
- database dump metadata
- hash-chain metadata, including first/last event IDs and final event hash
- checksum file reference

### `audit-backup.sql.gz`

Purpose: PostgreSQL audit-log restore fixture.

Contains:

- `compliance_audit_log` table DDL
- 100 deterministic audit events
- events ordered chronologically at one-minute intervals
- namespace fixed to `ordinox-ai`
- agent identities from the Synthetic Enterprise agent model
- decisions distributed across `allowed`, `requires_approval`, and `rejected`
- deterministic SHA-256 hash-chain fields:
  - `previous_hash`
  - `event_hash`

Hash input format:

```text
event_id|occurred_at|namespace|agent_id|project_id|action|decision|policy_version|reason|previous_hash
```

### `secrets-backup.json`

Purpose: Redacted/encrypted secret inventory for restore workflow validation.

Contains:

- `llm-api-keys`
  - `ANTHROPIC_API_KEY`
  - sealed placeholder URI
  - SHA-256 fingerprint of fixture placeholder
- `postgres-credentials`
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
  - `DATABASE_URL`
  - sealed placeholder URIs
  - SHA-256 fingerprints

No live secret material is present. Values are represented as
`sealed://ordinox-ai/...` references.

### `pvc/redis/appendonly.aof`

Purpose: Minimal Redis AOF snapshot for compliance runtime state.

Contains sample commands for:

- selected database
- global kill-switch state
- active policy version
- audit event index entries

### `pvc/qdrant/collections.json`

Purpose: Qdrant collection metadata restore fixture.

Contains:

- `compliance_regulations`
  - vector size
  - distance metric
  - payload schema
  - alias metadata
- `audit_event_embeddings`
  - vector count matching 100 audit events
  - payload schema
  - alias metadata

### `checksums.sha256`

Purpose: Integrity validation before restore.

Contains SHA-256 checksums for:

- `backup-manifest.json`
- `audit-backup.sql.gz`
- `secrets-backup.json`
- `pvc/redis/appendonly.aof`
- `pvc/qdrant/collections.json`

## Restore Validation Checklist

Use this checklist during Sprint 8 DR restore testing.

- [ ] Extract archive into an isolated restore workspace.
- [ ] Verify `checksums.sha256` before reading or restoring data.
- [ ] Confirm `backup-manifest.json` namespace is `ordinox-ai`.
- [ ] Confirm manifest cluster is `ordinox-talos-ha`.
- [ ] Confirm manifest resource count is `15`.
- [ ] Decompress `audit-backup.sql.gz`.
- [ ] Restore `audit-backup.sql` into the target PostgreSQL restore database.
- [ ] Verify `SELECT COUNT(*) FROM compliance_audit_log;` returns `100`.
- [ ] Verify `occurred_at` is monotonic from `audit-0001` through `audit-0100`.
- [ ] Recompute every event hash using the documented hash input format.
- [ ] Confirm every row's `previous_hash` matches the prior row's `event_hash`.
- [ ] Confirm the final recomputed hash matches `database.final_event_hash` in the manifest.
- [ ] Confirm `secrets-backup.json` contains no raw secret values.
- [ ] Confirm Redis AOF contains the active policy version.
- [ ] Confirm Qdrant metadata contains `compliance_regulations`.
- [ ] Confirm Qdrant metadata contains `audit_event_embeddings`.
- [ ] Record restore start time, restore end time, measured RTO, and measured RPO.

## Example Validation Commands

Extract:

```bash
mkdir -p /tmp/sprint8-dr-restore
tar -xzf tests/fixtures/sample-dr-backup.tar.gz -C /tmp/sprint8-dr-restore
cd /tmp/sprint8-dr-restore/dr-backup
```

Verify checksums:

```bash
sha256sum -c checksums.sha256
```

Inspect manifest:

```bash
jq '.namespace, .cluster, .resources, .database.audit_event_count' backup-manifest.json
```

Decompress audit dump:

```bash
gzip -dc audit-backup.sql.gz > audit-backup.sql
grep -c '^INSERT INTO compliance_audit_log' audit-backup.sql
```

Expected insert count:

```text
100
```

Restore into PostgreSQL:

```bash
psql "$DATABASE_URL" -f audit-backup.sql
psql "$DATABASE_URL" -c 'SELECT COUNT(*) FROM compliance_audit_log;'
```

## Pass Criteria

The DR fixture restore passes when:

- checksums validate with no failures
- manifest matches `ordinox-ai` and `ordinox-talos-ha`
- 100 audit events restore successfully
- audit events are chronological
- hash-chain recomputation succeeds end-to-end
- redacted secrets restore as metadata only, with no raw key exposure
- Redis and Qdrant fixture metadata are readable

## Fail Criteria

Stop the DR test and escalate if:

- checksum validation fails
- archive is missing any required file
- audit insert count is not exactly 100
- any event hash fails recomputation
- any raw secret value appears in `secrets-backup.json`
- namespace or cluster metadata does not match the target environment
- restore exceeds the Sprint 8 RTO/RPO thresholds documented in
  `chatgpt/DR-RESTORE-SCENARIOS.md`
