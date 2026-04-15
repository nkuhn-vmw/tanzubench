# TanzuBench

Open benchmark suite for LLMs running on the Tanzu GenAI tile. Measures what
users actually care about: can I use this model interactively on CPU? How does
it compare to GPU? Which model size is the sweet spot for my hardware?

**Live leaderboard:** [tanzubench.apps.tas-ndc.kuhn-labs.com](https://tanzubench.apps.tas-ndc.kuhn-labs.com/)

---

## What it measures

99 tests across 18 categories, scored by a pluggable grading system:

| Category | Tests | What it measures | Grader |
|---|---|---|---|
| **basic** | 3 | Factual Q&A, math | exact_match |
| **tool_use** | 6 | Function calling (single, dual, restraint) | tool_call |
| **structured_output** | 10 | JSON schema compliance, data extraction | json_schema |
| **coding** | 7 | Code generation across Python/JS/Bash/SQL | exec_unit_tests |
| **debugging** | 6 | Bug identification + fix across 6 bug classes | exec_unit_tests |
| **long_context** | 3 | Needle-in-haystack at 4K/16K/64K | needle |
| **instruction** | 4 | Instruction following (JSON-only, word count) | regex/contains |
| **file_ops** | 3 | File creation + content verification | file_check |
| **multi_turn** | 8 | Conversation coherence, context carryover, tool chaining | multi_turn |
| **monitoring** | 8 | Ops triage: crash loops, OOM, disk full, latency | contains/regex |
| **iac** | 8 | Infrastructure as code: K8s manifests, Dockerfiles, CF configs | exec_build |
| **ci_repair** | 6 | Fix broken builds: bad deps, syntax, Dockerfiles | exec_build |
| **reasoning** | 4 | Multi-hop reasoning over documents | llm_judge |
| **writing** | 3 | Summary, email, technical explanation | llm_judge |
| **research** | 2 | Synthesis with citations from multiple sources | llm_judge |
| **repo_patch** | 4 x 3 | SWE-bench-style repo-level bug fixes via 3 agent frameworks | agentic |
| **sysadmin** | 6 | System administration: cron, nginx, firewall, systemd | container_exec |
| **agentic** | 8 x 3 | Real coding agent tasks via goose/aider/custom | agentic |

---

## Latest results (DEV210, CPU — Gemma 4 E4B)

```
Model: gemma4:e4b  |  Foundation: DEV210  |  Hardware: CPU (Xeon)
Tile: v0.6.8  |  Engine: Ollama  |  Tests: 123  |  Categories: 18/18

Category             Score  Tasks  Notes
─────────────────────────────────────────────────
basic                1.000    3
debugging            1.000    6
file_ops             1.000    3
sysadmin             0.833    6    local fallback (no Docker)
coding               0.800    7
instruction          0.750    4
tool_use             0.667    6
multi_turn           0.625    8
structured_output    0.574   10
agentic              0.567   24    goose/aider/custom
long_context         0.333    3    64K times out on CPU
ci_repair            0.333    6
repo_patch           0.292   12    goose/aider/custom
iac                  0.250    8
monitoring           0.000    8    all timeout on CPU
reasoning            0.000    4    self-judge (needs GPU judge)
writing              0.000    3    self-judge (needs GPU judge)
research             0.000    2    self-judge (needs GPU judge)
─────────────────────────────────────────────────
Composite            0.501  123    0 skipped categories

Agent framework breakdown:
  goose:   0.412  (8 tasks)
  aider:   0.412  (8 tasks)
  custom:  0.875  (8 tasks)
```

**Key findings:**
- Custom in-process loop dominates (0.875) because it gets unlimited turns and
  direct tool access. Goose and aider are limited by turn caps and subprocess overhead
  on CPU, converging at 0.412 each.
- Monitoring scores 0 because every test times out — the model produces correct
  triage scripts but CPU inference takes 80-120s per response, exceeding the 120s
  per-test usability budget. A GPU would change this category dramatically.
- reasoning/writing/research score 0 due to self-judging. A gemma4:e4b judging its
  own output is unreliable. A dedicated GPU judge (e.g., Qwen3.5-27B on TDC) would
  produce real scores here.

---

## How scoring works

```
  tests/*.yaml ──→ bench_suite.py ──→ graders/* ──→ score per test (0.0 - 1.0)
                                                          │
                                                   per-category mean
                                                          │
                                                   composite score
                                                   (equal-weighted across
                                                    all 18 categories)
```

**Usability budgets:** Each test has a timeout. If the model produces a correct
answer but takes too long, it scores **0**. A 90-second answer to "What is 2+2?"
is not a useful answer. This makes CPU-vs-GPU comparisons honest.

**Judge-graded categories** (reasoning, writing, research) use a separate LLM as
judge. When no judge is configured, those categories score 0 (status: error). For
reliable judge scores, use a capable GPU model as judge, not the model under test.

**Agentic tests** run each task through 3 frameworks (goose, aider, custom loop).
The score is the mean across frameworks — giving "model quality vs framework quality"
signal.

**CPU vs GPU on one leaderboard:** Both run ALL 99 tests. CPU models that time out
on hard categories get honest zeros, pulling their composite down. No separate test
suites — one benchmark, comparable numbers.

---

## Quickstart

### Prerequisites

```bash
python3 --version   # 3.9+
node --version      # 20+
pip install jsonschema pyyaml
```

### 1. Run the benchmark

```bash
git clone https://github.com/nkuhn-vmw/tanzubench && cd tanzubench

# Against a local vLLM or Ollama endpoint
python3 tools/bench_suite.py \
  --url http://localhost:4000 \
  --model "your-model-name" \
  --engine vllm \
  --foundation local --hardware gpu \
  --suppress-thinking \
  --no-interactive
```

### 2. For CPU models (cap slow tests)

```bash
python3 tools/bench_suite.py \
  --url http://localhost:11434 \
  --model "gemma4:e4b" \
  --engine ollama \
  --foundation local --hardware cpu \
  --task-timeout 120 \
  --suppress-thinking \
  --no-interactive
```

`--task-timeout 120` = no test gets more than 2 minutes. Tests that exceed
this score 0 — that's the signal.

### 3. With a judge (enables reasoning, writing, research)

```bash
python3 tools/bench_suite.py \
  --url http://localhost:4000 \
  --model "target-model" \
  --engine vllm \
  --foundation local --hardware gpu \
  --judge-url http://<judge-host>/v1 \
  --judge-model "judge-model-name" \
  --suppress-thinking \
  --no-interactive
```

### 4. View results

```bash
python3 tools/format-results.py results/local/gpu/*.json
```

### 5. Run the leaderboard locally

```bash
cd web && npm install && npm run dev   # http://localhost:3000
```

---

## Architecture

```
tanzubench/
├── schema/                        # JSON Schema contracts
│   ├── result-v2.schema.json      #   every result file validates against this
│   └── test-v1.schema.json        #   every test YAML validates against this
│
├── tests/                         # 99 declarative test definitions (YAML)
│   ├── <category>/*.yaml          #   one file per test
│   ├── agentic/fixtures/          #   seed git repos for agent tasks
│   └── assets/                    #   haystacks, source docs, log samples
│
├── tools/
│   ├── bench_suite.py             # Main runner
│   ├── graders/                   # 13 pluggable grading plugins
│   ├── agents/                    # goose, aider, custom_loop adapters
│   ├── validate.py                # Schema validator
│   ├── format-results.py          # Pretty-print results
│   └── compare-results.py         # Side-by-side comparison
│
├── results/                       # One JSON per benchmark run
│   └── <foundation>/<hardware>/
│
├── web/                           # Next.js 14 leaderboard (static export)
│   ├── app/                       #   pages: /, /result/[id], /compare, etc.
│   ├── components/                #   UI components
│   └── lib/                       #   Zod schema mirror, loader, helpers
│
├── tile/                          # OpsManager tile (BOSH release)
│   ├── tile.yml                   #   tile-generator definition
│   ├── jobs/                      #   BOSH job templates
│   ├── packages/                  #   air-gap packaging
│   ├── src/tanzubench-server/     #   Go HTTP server for dashboard
│   └── scripts/                   #   build-tile.sh, vendor-tanzubench.sh
│
├── bench.sh                       # Thin wrapper
├── .env.example                   # Environment variable reference
└── .github/workflows/ci.yml       # CI + auto-deploy to Cloud Foundry
```

### Grader reference

| Grader | Categories | How it scores |
|---|---|---|
| exact_match | basic | String equality after normalization |
| contains | basic, monitoring | Response contains expected substring |
| regex | instruction | Response matches regex pattern |
| tool_call | tool_use | Correct function name + arguments |
| needle | long_context | Unicode-normalized needle-in-haystack |
| file_check | file_ops | File exists with expected content |
| exec_unit_tests | coding, debugging | Execute code, run unit tests |
| json_schema | structured_output | Parse JSON, validate schema, check values |
| multi_turn | multi_turn | Per-turn checks across conversation |
| llm_judge | reasoning, writing, research | LLM rubric scoring (0-5 scale) |
| exec_build | ci_repair, iac | Model fixes config, grader runs build command |
| container_exec | sysadmin | Execute in Docker container (local fallback if no Docker) |
| agentic | agentic, repo_patch | 3-framework fan-out: goose, aider, custom |

### Agent frameworks

| Framework | What it is | How it runs |
|---|---|---|
| **goose** | [Block Goose](https://github.com/block/goose) v1.30+ | `goose run --provider openai --model <name> --no-session --with-builtin developer` |
| **aider** | [Aider](https://aider.chat) | `aider --model openai/<name> --openai-api-base <url> --yes --no-auto-commits` |
| **custom** | In-process tool loop | 20-turn max, direct function calling with file read/write/shell tools |

---

## Full command reference

```
python3 tools/bench_suite.py [options]

Required:
  --url <endpoint>          OpenAI-compatible model endpoint
  --model <name>            Model name as served by the endpoint
  --foundation <name>       Foundation name (for result file paths)
  --hardware cpu|gpu        Hardware tier

Optional:
  --engine vllm|ollama|other         Default: vllm
  --api-key <key>                    Target model API key
  --judge-url <endpoint>             Judge model endpoint
  --judge-model <name>               Judge model name
  --judge-api-key <key>              Judge API key
  --max-run-time <seconds>           Total run cap (default: 7200 = 2hr)
  --task-timeout <seconds>           Per-test cap (overrides YAML budgets)
  --suppress-thinking                Suppress reasoning tokens (Gemma 4, Qwen3)
  --categories <list>                Comma-separated filter
  --runs N                           Repeat tests N times, report median
  --tile-version <ver>               GenAI tile version stored in result metadata
  --engine-config <json>             Manual engine overrides (tensor_parallel_size, etc.)
  --tag <label>                      Tag stored in meta.tag
  --no-interactive                   Don't prompt
```

---

## OpsManager tile

TanzuBench ships as an OpsManager tile for air-gapped deployment on
Tanzu Application Service. The tile includes:

- **Local leaderboard** — Next.js static site served via gorouter
- **Run benchmarks errand** — triggers the full 99-test suite
- **Export results errand** — packages results for download
- **Smoke tests** — verifies the model endpoint is reachable

All dependencies (Go server, Python wheels, aider, goose binary, cf CLI,
git) are vendored as BOSH blobs for air-gap operation.

```bash
# Build the tile
tile/scripts/build-tile.sh 0.6.8

# Run benchmarks on a deployed tile
bosh -d <deployment> run-errand run-benchmarks --keep-alive
```

See `tile/README.md` for build prerequisites and deployment instructions.

---

## Adding a test

```yaml
# tests/<category>/<id>.yaml
id: my-test-name          # must match filename
name: Human-readable name
category: coding           # one of 18 categories
grader: exec_unit_tests    # one of 13 graders
timeout_sec: 60            # usability budget
prompt: |
  Your prompt here...
grader_config:
  language: python
  entrypoint: my_function
  unit_tests:
    - {input: [1, 2], expected: 3}
```

1. Write the YAML
2. Validate: `python3 tools/validate.py --tests tests/`
3. Test: `python3 tools/bench_suite.py --categories coding ...`
4. Commit and push

See `docs/test-suite.md` for the full per-grader reference.

---

## Thinking token suppression

Gemma 4 and Qwen3 emit reasoning tokens that dominate CPU latency. Use
`--suppress-thinking` to prepend a system message telling the model to
respond directly. Measured impact: 3.2x speedup on Gemma 4 E4B.

---

## Tool requirements

| Tool | Required for | Install |
|---|---|---|
| **Python 3.9+** | Runner, graders | System |
| **jsonschema** | Schema validation | `pip install jsonschema` |
| **pyyaml** | Test YAML loading | `pip install pyyaml` |
| Node.js 20+ | Web leaderboard | System |
| goose 1.30+ | Agentic tests (goose framework) | [block/goose](https://github.com/block/goose) |
| aider | Agentic tests (aider framework) | `pip install aider-chat` |
| Docker | Sysadmin tests (container_exec) | Optional — falls back to local execution |
| cf CLI v8+ | Leaderboard deployment | [cloudfoundry/cli](https://github.com/cloudfoundry/cli) |

**Bold = required for core benchmark.** Everything else is optional.

---

## License

Apache 2.0
