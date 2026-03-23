#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d "$ROOT_DIR/.lockcheck.XXXXXX")"
NORM_DIR="$(mktemp -d "$ROOT_DIR/.lockcheck.norm.XXXXXX")"
trap 'rm -rf "$TMP_DIR" "$NORM_DIR"' EXIT

"$ROOT_DIR/scripts/compile_lockfiles.sh" --output-dir "$TMP_DIR"

normalize_lockfile() {
  local src="$1"
  local dst="$2"
  python3 - "$src" "$dst" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
lines = src.read_text(encoding="utf-8").splitlines()
out: list[str] = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith("greenlet=="):
        i += 1
        while i < len(lines) and lines[i].startswith("    --hash="):
            i += 1
        continue
    out.append(line)
    i += 1
dst.write_text("\n".join(out) + "\n", encoding="utf-8")
PY
}

normalize_lockfile "$ROOT_DIR/requirements.lock" "$NORM_DIR/current-requirements.lock"
normalize_lockfile "$TMP_DIR/requirements.lock" "$NORM_DIR/new-requirements.lock"

diff -u "$NORM_DIR/current-requirements.lock" "$NORM_DIR/new-requirements.lock"
diff -u "$ROOT_DIR/requirements-dev.lock" "$TMP_DIR/requirements-dev.lock"

echo "Lock files are in sync."
