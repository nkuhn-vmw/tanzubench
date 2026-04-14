#!/bin/bash
set -euo pipefail

# Vendors the tanzubench benchmark suite into tile/src/tanzubench/ for BOSH packaging.
# Run from anywhere — resolves paths relative to the repo root.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TILE_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$TILE_DIR")"

echo "Vendoring tanzubench from $REPO_ROOT into $TILE_DIR/src/tanzubench/..."

TARGET="$TILE_DIR/src/tanzubench"
rm -rf "$TARGET"
mkdir -p "$TARGET"

# Copy the benchmark suite (tools, tests, schema)
cp -r "$REPO_ROOT/tools" "$TARGET/"
cp -r "$REPO_ROOT/tests" "$TARGET/"
cp -r "$REPO_ROOT/schema" "$TARGET/"

# Pre-build the web leaderboard
echo "Building web leaderboard..."
(cd "$REPO_ROOT/web" && npm ci && npm run build)
mkdir -p "$TARGET/web"
cp -r "$REPO_ROOT/web/out" "$TARGET/web/out"

# Replace pip install pytest with PYTHONPATH setup (pytest is vendored)
find "$TARGET/tests/agentic" -name "*.yaml" -exec sed -i.bak \
  "s|python3 -m pip install -q pytest|export PYTHONPATH=/var/vcap/packages/tanzubench/python-lib:\$PYTHONPATH 2>/dev/null || true|" {} \;
find "$TARGET/tests/agentic" -name "*.bak" -delete
echo "Replaced pip install with PYTHONPATH setup in agentic tests"

echo "Vendored to $TARGET ($(du -sh "$TARGET" | cut -f1))"
