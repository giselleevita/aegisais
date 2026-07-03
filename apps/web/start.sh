#!/bin/bash
# Script to ensure correct Node version is used

export NVM_DIR="$HOME/.nvm"
[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"

# Use Node 26 (see .nvmrc)
nvm use 26 2>/dev/null || nvm use

# Verify Node version
NODE_VERSION=$(node --version)
echo "Using Node.js: $NODE_VERSION"

if [[ ! "$NODE_VERSION" =~ ^v20\.(19|[2-9][0-9])|^v22\.(1[2-9]|[2-9][0-9])|^v2[4-9]\. ]]; then
  echo "Error: Node.js 20.19+, 22.12+, or 24+ required. Current version: $NODE_VERSION"
  echo "Please run: nvm use"
  exit 1
fi

# Run the command passed as arguments
exec "$@"


