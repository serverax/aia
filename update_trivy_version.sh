#!/bin/bash

# Set the path to the CI workflow file
WORKFLOW_FILE=".github/workflows/ci.yml"

# Set the desired Trivy action version
TRIVY_VERSION="0.9.2"

# Update the Trivy action version in the workflow file
sed -i "s/aquasecurity\/trivy-action@.*/aquasecurity\/trivy-action@$TRIVY_VERSION/" "$WORKFLOW_FILE"

echo "Updated Trivy action version to $TRIVY_VERSION in $WORKFLOW_FILE"
