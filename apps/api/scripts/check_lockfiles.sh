#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "$ROOT_DIR/.lockcheck.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

"$ROOT_DIR/scripts/compile_lockfiles.sh" --output-dir "$TMP_DIR"

diff -u "$ROOT_DIR/requirements.lock" "$TMP_DIR/requirements.lock"
diff -u "$ROOT_DIR/requirements-dev.lock" "$TMP_DIR/requirements-dev.lock"

echo "Lock files are in sync."
