# TanzuBench Tile

OpsManager tile for deploying TanzuBench on Tanzu Application Service.

This directory contains the BOSH release and tile-generator config.
The benchmark suite (`tools/`, `tests/`, `schema/`, `web/`) lives at the
repo root and is vendored into `tile/src/tanzubench/` at build time.

## What's in the tile

- **Local leaderboard** — Next.js static site served via gorouter
- **Run benchmarks errand** — triggers the full test suite against a configured model endpoint
- **Export results errand** — packages results for download
- **Smoke tests** — verifies the model endpoint is reachable

## Building

```bash
# From the repo root:
pip install tile-generator
tile/scripts/build-tile.sh 0.6.3
```

The build script vendors the benchmark suite, builds the BOSH release,
and runs tile-generator. Blobs must be present in `tile/blobs/` (see below).

## Blobs (air-gap dependencies)

Place these in `tile/blobs/` before building:

| Blob | Contents |
|------|----------|
| `golang/go1.22.12.linux-amd64.tar.gz` | Go compiler for tanzubench-server |
| `cf-cli/cf8-cli-linux64.tgz` | CF CLI for marketplace binding |
| `python-deps/*.whl` | jsonschema, pyyaml, typing_extensions |
| `aider/aider-wheels.tar.gz` | aider-chat + all Python deps |
| `goose/goose-linux.tar.gz` | Goose v1.30.0 Linux AMD64 binary |
| `git/git-debs.tar.gz` | git binary for agentic fixtures |

## Deploying

1. Upload `tile/product/tanzubench-<version>.pivotal` to OpsManager
2. Configure the GenAI model endpoint in tile settings
3. Apply changes
4. Run benchmarks: `bosh -d <deployment> run-errand run-benchmarks`
5. View results at `https://tanzubench.<system-domain>/`
