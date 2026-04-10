# TanzuBench

Open benchmark suite for LLMs running on the Tanzu GenAI tile. Measures what
users actually care about: can I use this model interactively on CPU? How does
it compare to GPU? Which model size is the sweet spot for my hardware?

**Live leaderboard:** [tanzubench.apps.tas-ndc.kuhn-labs.com](https://tanzubench.apps.tas-ndc.kuhn-labs.com/)

---

## What it measures

67 tests across 13 categories, scored by a pluggable grading system:

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
| **reasoning** | 4 | Multi-hop reasoning over documents | llm_judge |
| **writing** | 3 | Summary, email, technical explanation | llm_judge |
| **research** | 2 | Synthesis with citations from multiple sources | llm_judge |
| **agentic** | 8 x 3 | Real coding agent tasks via opencode/aider/custom | agentic |

---

## How scoring works

```
  tests/*.yaml ──→ bench_suite.py ──→ graders/* ──→ score per test (0.0 - 1.0)
                                                          │
                                                   per-category mean
                                                          │
                                                   composite score
                                                   (equal-weighted across
                                                    all 13 categories)
```

**Usability budgets:** Each test has a timeout. If the model produces a correct
answer but takes too long, it scores **0**. A 90-second answer to "What is 2+2?"
is not a useful answer. This makes CPU-vs-GPU comparisons honest.

**Judge-graded categories** (reasoning, writing, research) use a separate LLM as
judge. When no judge is configured, those categories are skipped.

**Agentic tests** run each task through 3 frameworks (opencode, aider, custom loop).
The score is the mean across frameworks — giving "model quality vs framework quality" signal.

**CPU vs GPU on one leaderboard:** Both run ALL 67 tests. CPU models that time out
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

### 3. With a judge (enables 3 more categories)

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
├── tests/                         # 67 declarative test definitions (YAML)
│   ├── <category>/*.yaml          #   one file per test
│   ├── agentic/fixtures/          #   seed git repos for agent tasks
│   └── assets/                    #   haystacks, source docs, log samples
│
├── tools/
│   ├── bench_suite.py             # Main runner
│   ├── graders/                   # 11 pluggable grading plugins
│   ├── agents/                    # opencode, aider, custom_loop adapters
│   ├── validate.py                # Schema validator
│   ├── format-results.py          # Pretty-print results
│   ├── compare-results.py         # Side-by-side comparison
│   └── bosh_tunnel.sh             # Stable BOSH SSH port-forward
│
├── results/                       # One JSON per benchmark run
│   └── <foundation>/<hardware>/
│
├── web/                           # Next.js 14 leaderboard (static export)
│   ├── app/                       #   pages: /, /result/[id], /compare, etc.
│   ├── components/                #   UI components
│   └── lib/                       #   Zod schema mirror, loader, helpers
│
├── bench.sh                       # Thin wrapper
├── .env.example                   # Environment variable reference
└── .github/workflows/ci.yml       # CI + auto-deploy to Cloud Foundry
```

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
  --tag <label>                      Tag stored in meta.tag
  --no-interactive                   Don't prompt
```

---

## Adding a test

```yaml
# tests/<category>/<id>.yaml
id: my-test-name          # must match filename
name: Human-readable name
category: coding           # one of 13 categories
grader: exec_unit_tests    # one of 11 graders
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

## Deploying the leaderboard to Cloud Foundry

The leaderboard is a static Next.js site. It auto-deploys on push to `main`
via GitHub Actions.

```yaml
# web/manifest.yml
applications:
  - name: tanzubench
    memory: 64M
    buildpacks: [staticfile_buildpack]
    path: ./out
    env:
      FORCE_HTTPS: true
```

First-time setup: see `docs/deployment.md`.

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
| aider | Agentic tests (aider framework) | `pip install aider-chat` |
| opencode | Agentic tests (opencode framework) | [opencode.ai](https://opencode.ai) |
| cf CLI v8+ | Leaderboard deployment | [cloudfoundry/cli](https://github.com/cloudfoundry/cli) |

**Bold = required for core benchmark.** Everything else is optional.

---

## License

Apache 2.0
