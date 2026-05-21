#!/usr/bin/env bash
set -euo pipefail

FIXTURE="${1:-tests/fixtures/mock-kubectl-responses.json}"

python3 - "$FIXTURE" <<'PY'
import json
import sys
from pathlib import Path

fixture = Path(sys.argv[1])
data = json.loads(fixture.read_text())

required = [
    "context",
    "nodes",
    "deployments",
    "pods",
    "services",
    "endpoints",
    "events",
    "rollout_history",
    "rollout_status",
]

missing = [key for key in required if key not in data]
if missing:
    raise SystemExit(f"missing keys: {missing}")

failed = [key for key in required if data[key].get("status") != 0]
if failed:
    raise SystemExit(f"non-zero mock statuses: {failed}")

if "Ready" not in data["nodes"]["output"]:
    raise SystemExit("nodes output does not include Ready")
if "2/2" not in data["deployments"]["output"]:
    raise SystemExit("deployment output does not include 2/2")
if ":8000" not in data["endpoints"]["output"]:
    raise SystemExit("endpoints output does not include :8000")

print("fixture_valid=true")
print("fixture=" + str(fixture))
print("keys=" + ",".join(required))
PY

