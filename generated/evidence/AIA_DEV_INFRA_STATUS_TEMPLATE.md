# AIA DEV Infrastructure Status

## Generated Files

Run:

```bash
find /mnt/f/aia-dev/generated -type f | sort
```

Paste output here.

## Kubernetes Evidence

Run:

```bash
kubectl get ns | grep aia-dev
kubectl -n aia-dev get pods -o wide
kubectl -n aia-dev-storage get pods -o wide
kubectl -n aia-dev get svc
kubectl -n aia-dev get ingress -o wide
```

Paste output here.

## Database Evidence

Run:

```bash
psql "$DATABASE_URL" -f /mnt/f/aia-dev/generated/supabase/aia_dev_schema.sql
```

Then verify:

```sql
select schema_name
from information_schema.schemata
where schema_name in ('orchestrator_dev', 'rag_dev', 'semantic_dev');

select table_schema, table_name
from information_schema.tables
where table_schema in ('orchestrator_dev', 'rag_dev', 'semantic_dev')
order by table_schema, table_name;
```

Paste output here.

## DNS Evidence

Run:

```bash
dig +short dev.ordinoxai.com
curl -I https://dev.ordinoxai.com
```

Paste output here.

## Final Status

| Area | Status |
|---|---|
| K8s namespaces | Pending evidence |
| Storage | Pending evidence |
| LLM | Pending evidence |
| Workers | Pending evidence |
| Ingress | Pending evidence |
| DB schemas | Pending evidence |
| CI/CD | Pending evidence |
| DNS | Manual / pending evidence |
