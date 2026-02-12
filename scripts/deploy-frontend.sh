#!/bin/bash
set -euo pipefail

echo "=== Deploying Frontend to Vercel ==="

# Check prerequisites
command -v vercel >/dev/null 2>&1 || { echo "Vercel CLI not found. Install with: npm i -g vercel"; exit 1; }

cd frontend

# Install dependencies
echo "Installing frontend dependencies..."
npm install

# Build
echo "Building frontend..."
npm run build

# Deploy
echo "Deploying to Vercel..."
vercel --prod

echo ""
echo "=== Frontend deployment complete ==="
