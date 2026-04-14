#!/bin/bash
set -euo pipefail

VERSION="${1:?Usage: build-tile.sh <version>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TILE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Building TanzuBench tile v${VERSION} ==="

# Step 1: Vendor tanzubench from repo root into tile/src/tanzubench/
echo "Vendoring benchmark suite..."
"$SCRIPT_DIR/vendor-tanzubench.sh"

# Step 2: Build the BOSH release
echo "Building BOSH release..."
cd "$TILE_DIR"
bosh create-release --force --version="${VERSION}" --tarball="resources/tanzubench-release.tgz"

# Step 3: Download dependency releases (BPM)
echo "Downloading BPM release..."
[ -f resources/bpm-release.tgz ] || \
  curl -sL "https://bosh.io/d/github.com/cloudfoundry/bpm-release?v=1.4.23" \
    -o resources/bpm-release.tgz

# Step 4: Patch tile.yml with version
sed -i.bak "s/^  version: .*/  version: '${VERSION}'/" tile.yml
rm -f tile.yml.bak

# Step 5: Build the tile
echo "Running tile-generator..."
tile build "${VERSION}"

# Step 6: Post-build fix for errand boolean bug
# (tile-generator writes 'false' as string instead of boolean)
PIVOTAL="product/tanzubench-${VERSION}.pivotal"
if [ -f "$PIVOTAL" ]; then
  echo "Patching errand boolean bug..."
  TMPDIR=$(mktemp -d)
  cd "$TMPDIR"
  unzip -q "$TILE_DIR/$PIVOTAL"
  find . -name "*.yml" -exec sed -i.bak \
    "s/run_post_deploy_errand_default: 'false'/run_post_deploy_errand_default: false/g" {} \;
  find . -name "*.bak" -delete
  zip -q -r "$TILE_DIR/$PIVOTAL" .
  cd "$TILE_DIR"
  rm -rf "$TMPDIR"
fi

echo "=== Tile built: $PIVOTAL ==="
ls -lh "$PIVOTAL"
