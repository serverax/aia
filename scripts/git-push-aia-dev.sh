#!/usr/bin/env bash
set -euo pipefail

BRANCH="${BRANCH:-dev}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-chore: add AIA dev infrastructure automation}"

echo "=================================================="
echo "AIA local Git push helper"
echo "Branch: ${BRANCH}"
echo "Message: ${COMMIT_MESSAGE}"
echo "=================================================="

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: this directory is not a Git repository."
  echo "Run from your repo root or initialise/connect the repo first."
  exit 1
fi

echo "Current remotes:"
git remote -v || true

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: no git remote named origin."
  echo "Add it first, example:"
  echo "  git remote add origin https://github.com/serverax/<repo-name>.git"
  exit 1
fi

git status -sb

git checkout -B "${BRANCH}"

git add \
  .github/workflows/aia-dev-ci.yml \
  .github/workflows/aia-dev-build-images.yml \
  .github/workflows/aia-dev-deploy-k8s.yml \
  scripts/aia-dev-full-infra-auto.sh \
  scripts/aia-dev-cicd-docs-auto.sh \
  scripts/git-push-aia-dev.sh \
  scripts/verify-aia-dev-infra.sh \
  docs/aia \
  generated/supabase \
  generated/k8s \
  generated/dns \
  generated/docs || true

if git diff --cached --quiet; then
  echo "No changes staged."
else
  git commit -m "${COMMIT_MESSAGE}"
fi

git push -u origin "${BRANCH}"

echo "Pushed to origin/${BRANCH}"
