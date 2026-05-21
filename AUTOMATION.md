# Automation Guide

## Makefile Commands
- `make install` - Install deps
- `make test` - Run tests
- `make lint` - Lint code
- `make format` - Format code
- `make build` - Build Docker
- `make deploy` - Deploy to K3s
- `make verify` - Verify project
- `make all` - Full pipeline

## GitHub Actions
- **ci.yml** - Test, build, deploy on push
- **quality.yml** - Code analysis

## Talos & K3s
- Namespace: synthetic-enterprise
- Resource Quotas: 100 CPU, 200Gi RAM
- Network Policies: Deny-all, allow internal

## Workflow
1. Code -> 2. Test -> 3. Lint -> 4. Format -> 5. Commit -> 6. Push -> 7. GitHub Actions

Check deployment:

```
kubectl get all -n synthetic-enterprise
```
