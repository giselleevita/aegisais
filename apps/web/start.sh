#!/bin/bash
# Script to ensure correct Node version is used

export NVM_DIR="$HOME/.nvm"
[ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"

# Use Node 20.19.0
nvm use 20.19.0

# Verify Node version
NODE_VERSION=$(node --version)
echo "Using Node.js: $NODE_VERSION"

if [[ ! "$NODE_VERSION" =~ ^v20\.(19|2[0-9])|^v22\.(1[2-9]|[2-9][0-9]) ]]; then
  echo "Error: Node.js 20.19+ or 22.12+ required. Current version: $NODE_VERSION"
  echo "Please run: nvm use 20.19.0"
  exit 1
fi

# Run the command passed as arguments
exec "$@"


