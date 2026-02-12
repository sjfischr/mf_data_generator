#!/bin/bash
set -euo pipefail

echo "=== Deploying Backend Infrastructure ==="

# Check prerequisites
command -v cdk >/dev/null 2>&1 || { echo "AWS CDK CLI not found. Install with: npm install -g aws-cdk"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 not found."; exit 1; }

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Bootstrap CDK (first time only)
echo "Bootstrapping CDK..."
cdk bootstrap aws://${AWS_ACCOUNT_ID}/${AWS_REGION} 2>/dev/null || true

# Synthesize CloudFormation templates
echo "Synthesizing CDK stacks..."
cdk synth

# Deploy all stacks
echo "Deploying stacks..."
cdk deploy --all --require-approval never

echo ""
echo "=== Backend deployment complete ==="
echo "API Gateway URL will be in the stack outputs above."
