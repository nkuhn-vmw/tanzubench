# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo shape

Three subsystems joined by a JSON schema:

1. **Benchmark runner** (`tools/bench_suite.py`, `tools/graders/`, `tools/agents/`) — runs YAML-defined tests against an OpenAI-compatible endpoint, produces timestamped result JSON under `results/<foundation>/<hw>/`.
2. **Leaderboard webapp** (`web/`, Next.js 14 App Router, static export) — loads every file under `results/` at build time, validates with Zod against `schema/result-v2.schema.json`, and renders faceted views.
3. **OpsManager tile** (`tile/`) — BOSH release + tile-generator config for deploying TanzuBench on Tanzu Application Service. Contains BOSH jobs (web, run-benchmarks, export-results, smoke-tests), a Go HTTP server (`tile/src/tanzubench-server/`), and air-gap blob specs. The benchmark suite is vendored from the repo root into `tile/src/tanzubench/` at build time via `tile/scripts/vendor-tanzubench.sh`.

The two schemas are the contract:
- `schema/result-v2.schema.json` — shape of every result file. CI gates via `tools/validate.py`.
- `schema/test-v1.schema.json` — shape of every test YAML. `validate.py --tests` gates on this.

Changes to either schema must update the schema file, validator, web loader/types, and any fixtures together — otherwise CI or the web build breaks.

## Common commands

Web (run from `web/`):
```bash
npm install
npm run dev          # http://localhost:3000, live-reads ../results/
npm run build        # static export → web/out/
npm run lint
npm test             # Vitest unit + smoke
npx vitest run path/to/file.test.ts   # single test file
npx vitest run -t "name"              # single test by name
npm run test:e2e     # Playwright happy-path
```

Schema / results:
```bash
python3 tools/validate.py results/                # validate every result file (CI uses this)
python3 tools/validate.py --tests tests/          # validate every test YAML
python3 tools/format-results.py < results/.../x.json
python3 tools/compare-results.py a.json b.json
```

Benchmarks:
```bash
# Minimal run (no judge)
python3 tools/bench_suite.py \
  --url http://127.0.0.1:4000 --api-key "$API_KEY" \
  --model "Qwen3-32B-GPTQ-Int4" \
  --engine vllm --foundation tdc --hardware gpu \
  --gpu-count 2 --gpu-model "RTX 3090"

# With judge (enables reasoning/writing/research categories)
python3 tools/bench_suite.py \
  --url http://... --model ... --foundation tdc --hardware gpu \
  --judge-url http://<judge-endpoint>/v1 \
  --judge-model "Qwen3-32B" --judge-api-key "$JUDGE_KEY"

# Run only specific categories
python3 tools/bench_suite.py \
  --url http://... --model ... --foundation tdc --hardware gpu \
  --categories basic,coding,tool_use

# Validate test definitions
python3 tools/validate.py --tests tests/
```

Tile (run from repo root):
```bash
tile/scripts/build-tile.sh 0.6.3            # vendor + BOSH release + tile build
tile/scripts/vendor-tanzubench.sh           # vendor benchmark suite only
# Blobs must be in tile/blobs/ (gitignored, ~247MB total)
```

## Architecture notes

- **Foundations are first-class facets**: results are organized by `foundation` (cdc/dev210/tdc) and `hardware` (cpu/gpu) because the same model behaves very differently across infra. Filters in the leaderboard mirror this — don't collapse them.
- **18 test categories**: basic, tool_use, structured_output, coding, debugging, long_context, instruction, file_ops, multi_turn, reasoning, writing, research, monitoring, iac, ci_repair, repo_patch, sysadmin, agentic. The first ten run without a judge; reasoning/writing/research require `--judge-url`. Agentic additionally fans each task out across 3 agent frameworks (goose/aider/custom).
- **Judge fingerprint**: when `--judge-url` is set, the runner records a fingerprint of the judge endpoint. Results graded by different judges should not be compared directly — the leaderboard UI surfaces this.
- **3-framework agentic model**: each agentic task runs independently against goose, aider, and a custom single-turn loop. The spread lets you distinguish model limitations from framework integration issues. See `docs/agentic-harness.md`.
- **Static export**: `web/` is built with `next build` to a fully static site (no server runtime on the deploy target). All result loading happens at build time in `web/lib/`. There is no API route layer; if you need new data, it has to flow through the schema → loader path.
- **Pages**: `/` faceted leaderboard, `/foundations` + `/foundations/[slug]`, `/result/[id]` (Tests/Config/Raw tabs), `/compare?ids=a,b,c`, `/about`.
- **Thinking-token suppression**: modern models (Gemma 4, Qwen3) emit reasoning tokens that dominate CPU latency. The tile's `model_modelfile` SYSTEM directive is **not** forwarded through the GenAI tile proxy, so clients must inject the suppression system message themselves. See README for the exact message; relevant when touching the accuracy harness or interpreting CPU results.

## CI / deploy

- `.github/workflows/validate.yml` — PR gate: schema validation + web tests + web build.
- `.github/workflows/deploy.yml` — push to `main` auto-deploys the static export to Cloud Foundry on the NDC foundation. See `docs/deployment.md` for the one-time setup. Adding a result file and pushing to `main` is the entire publish flow.

## Adding a result

Run `tools/bench_suite.py`, validate with `python3 tools/validate.py results/`, commit under the right `results/<foundation>/<hw>/` path, push. Do not hand-edit historical result files.

## Adding a test

Write a YAML under `tests/<category>/`, run `python3 tools/validate.py --tests tests/`, then smoke-test with `--categories <cat>`. See `docs/test-suite.md` for the full contributor guide.
