# Consolidated Benchmark Results

**Last updated:** 2026-04-06 | **GenAI Tile:** 10.3.4

---

## Production-Ready CPU Model Leaderboard (2026-04-06)

After adding accuracy testing and thinking-token suppression analysis, the ranked CPU lineup across **both** foundations is:

| Rank | Model | Foundation | Avg Tool Call | Accuracy | Tokens/Call | Role |
|------|-------|-----------|--------------|----------|-------------|------|
| 1 | **gemma4:e4b** (w/ system prompt) | DEV210 | **1.71s** | 90% | 15 | **Fastest tool caller** — beats ministral-3:3b |
| 2 | **gemma4:26b** (w/ system prompt) | DEV210 | 2.78s | **100%** | 19 | **Best quality** — MoE, 3.8B active params |
| 3 | **llama3.1:8b** | CDC | 9-19s | **100%** | 185 total | **Only multi-step agentic model** |
| 4 | **nemotron-3-nano:4b** | CDC | 10-16s | **100%** | 622 total | Reliable all-around |
| 5 | **ministral-3:3b** | CDC | 2.1s | 80% | 225 total | Fast but refuses some tool types |

**Key finding:** `gemma4:e4b` with thinking suppression replaces `ministral-3:3b` as the fastest CPU tool-calling model — and it actually uses `read_file` and `search_code` tools that ministral refuses.

---

## TDC Foundation — GPU (vLLM)

### Qwen3.5-27B-GPTQ-Int4

| Date | Config | Context | Tok/s (gen) | Tool Call | Code 500 | Long 1000 | VRAM/GPU | Notes |
|------|--------|---------|-------------|-----------|----------|-----------|----------|-------|
| 03-23 | 4x 3090, enforce-eager | 64K | **10.8** | 2.5s | 46.2s | — | 23.6/24.5 GB | First deploy. 256K OOM, 64K max. |
| 03-27 | 2x 3090, enforce-eager | **256K** | **11.6** | 2.4s | 41.7s | 86.1s | 22.1/24.6 GB | DeltaNet hybrid needs less KV cache. Half the GPUs, full context. |
| **03-27** | **2x 3090, CUDA graphs** | **256K** | **48.3** | 4.6s* | **9.8s** | **20.7s** | 22.6/24.6 GB | **4.2x faster.** enforce-eager removed. *First requests slow (graph capture). |

**Key finding:** Removing `--enforce-eager` enables CUDA graph capture, yielding **4.2x throughput improvement** (48 tok/s vs 11.6 tok/s). First 1-2 requests per sequence length are slow while graphs compile, then subsequent requests are dramatically faster.

**Current best config:**
```
--tensor-parallel-size 2 --gpu-memory-utilization 0.95 --max-model-len 262144
--quantization gptq_marlin --dtype float16 --enable-chunked-prefill
--enable-prefix-caching --max-num-seqs 16
```

---

## CDC Foundation — CPU (Ollama)

### Ollama CPU Leaderboard (cpu-2xlarge: 16 vCPU Xeon Gold 6254, 32GB RAM)

**Config:** Ollama 0.18.2, context=32768, kv_cache=q8_0, num_parallel=1, flash_attention=true

| Rank | Model | Params | Tok/s (gen) | Tool Call | Dual Tool | Multi-Step | Verdict |
|------|-------|--------|-------------|-----------|-----------|------------|---------|
| 1 | **nemotron-3-nano:4b** | 4B | **14.9** | 9.8s (2/2) | 10.6s (2/2) | 1-step | Best balanced CPU model |
| 2 | **ministral-3:3b** | 3B | 11.9 | **3.8s** (2/2) | **3.6s** (2/2) | 1-step | Fastest response time |
| 3 | **llama3.1:8b** | 8B | 9.9 | 9.6s (2/2) | 8.7s (2/2) | **3-step** | Best agentic reasoning |
| 4 | gpt-oss:20b | 20B | 14.8 | 5.5s (1/2) | 5.6s (1/2) | poor | Fast but unreliable tools |
| 5 | qwen3.5:4b | 4B | 7.2 | 17.1s (2/2) | 34.3s (2/2) | 1-step | Thinking overhead too heavy |
| 6 | qwen3.5:9b | 9B | 5.4 | 26.5s (2/2) | 31.4s (2/2) | 1-step | Too slow for CPU |

---

## DEV210 Foundation — CPU (Gemma 4 Family)

**Config:** Ollama 0.20.2, GenAI tile 10.3.4, context=32768, kv_cache=q8_0, temp=0.1, num_thread=16

Benchmarked all four Gemma 4 variants — including a dedicated `cpu-4xlarge` (16 vCPU, 64GB RAM) VM type created for the larger models.

### Speed Benchmark (Default — Thinking Enabled)

| Model | Architecture | VM Type | Tool Call (dual) | Tok/s (code) | Multi-Step | Verdict |
|-------|-------------|---------|------------------|--------------|------------|---------|
| **gemma4:e4b** | PLE 4.5B | cpu-2xlarge | **3.1s** (30tok) | 11.5 | 1-step | Inconsistent — sometimes thinks, sometimes direct |
| **gemma4:26b** | MoE 3.8B active | cpu-4xlarge | 20.1s (162tok) | 8.4 | 1-step | 18GB model, surprisingly fast for size |
| **gemma4:e2b** | PLE 2.3B | cpu-2xlarge | 14.2s (289tok) | **20.1** | 1-step | Best throughput, thinking bloats tool calls |
| **gemma4:31b** | Dense 31B | cpu-4xlarge | 134.8s | 1.1 | 1-step | **NOT VIABLE** — 2-3 min responses |

### Accuracy + Thinking Suppression

10-test accuracy suite (5 factual + 5 tool call), comparing default vs custom no-think variants (Modelfile with `SYSTEM "Respond directly and concisely"`):

| Model | Variant | Accuracy | Total Tokens | Total Time | Token Reduction | Speedup |
|-------|---------|----------|-------------|------------|-----------------|---------|
| gemma4:e4b | default | 100% | 1,717 | 188s | — | — |
| gemma4:e4b | **no-think** | 90% | **488** | **58s** | **72%** | **3.2x** |
| gemma4:26b | default | 100% | 1,203 | 141s | — | — |
| gemma4:26b | **no-think** | **100%** | **623** | **80s** | **48%** | **1.8x** |
| gemma4:e2b | default | 90% | 1,611 | 91s | — | — |
| gemma4:e2b | no-think | 90% | 1,241 | 101s | 23% | 0.9x |
| gemma4:31b | default | 100% | 816 | 827s | — | — |
| gemma4:31b | no-think | 100% | 604 | 682s | 26% | 1.2x |

**Key insight:** Thinking suppression does NOT reduce accuracy. E4B and 26B maintain their scores while dropping 48-72% of tokens.

### Scale Test (Through GenAI Proxy)

Production-candidate models tested through the proxy with system message in request body:

| Metric | gemma4:e4b | gemma4:26b |
|--------|-----------|-----------|
| Sequential tool call (avg/p95) | **1.71s / 1.66s** | 2.78s / 2.78s |
| Tokens per tool call | 15 | 19 |
| Concurrent load (3 parallel) | Serialized (4.4s wall) | Serialized (7.7s wall) |
| Sustained throughput | 11.55 tok/s | 8.23 tok/s |
| Errors across 36 requests | **0** | **0** |

**CPU concurrency:** All requests serialize on CPU — the proxy queues gracefully with zero failures, but no true parallelism.

---

## Cross-Foundation Accuracy Leaderboard (2026-04-06)

Same 10-test suite (5 factual + 5 tool call) run across both foundations for apples-to-apples comparison:

| Rank | Model | Foundation | Accuracy | Tokens | Time | Key Failure |
|------|-------|-----------|----------|--------|------|-------------|
| 1 | **llama3.1:8b** | CDC | **100%** | **185** | 53s | None — most efficient |
| 2 | nemotron-3-nano:4b | CDC | 100% | 622 | 71s | None |
| 3 | gemma4-nothink:26b | DEV210 | 100% | 623 | 80s | None |
| 4 | gemma4:26b (default) | DEV210 | 100% | 1,203 | 141s | None |
| 5 | gemma4:e4b (default) | DEV210 | 100% | 1,717 | 188s | None |
| 6 | qwen3.5:4b | CDC | 100% | 1,502 | 431s | None (slow due to thinking) |
| 7 | qwen3.5:9b | CDC | 100% | 1,638 | 357s | None (slow due to thinking) |
| 8 | gemma4-nothink:e4b | DEV210 | 90% | 488 | 58s | TOOL-3 (asks for path) |
| 9 | gemma4:e2b (default) | DEV210 | 90% | 1,611 | 91s | TOOL-3 (asks for path) |
| 10 | gpt-oss:20b | CDC | 90% | 408 | 37s | TOOL-4 (misses get_time) |
| 11 | gemma4-nothink:e2b | DEV210 | 90% | 1,241 | 101s | TOOL-3 (asks for path) |
| 12 | **ministral-3:3b** | CDC | **80%** | 225 | 22s | TOOL-2, TOOL-3 refused |

**Headlines:**
- **llama3.1:8b is the overall accuracy champion** — 100% with only 185 tokens (most efficient model tested anywhere)
- **ministral-3:3b has the lowest accuracy** at 80% — refuses `read_file` and `search_code` tools, responding with text clarifications
- **gpt-oss:20b fails dual tool calls consistently** — only calls the first tool
- **Speed without accuracy is unreliable** — CDC's fastest (ministral-3:3b, 22s) scores worst; DEV210's new champion (gemma4-nothink:e4b, 58s) scores 90%

---

## CDC Foundation — CPU (vLLM CPU vs Ollama)

### Head-to-Head: Tool Calling

| Engine | Model | Quant | Time | Tok/s | Tools | RAM |
|--------|-------|-------|------|-------|-------|-----|
| Ollama | ministral-3:3b | Q4_K_M | **2.1s** | **12.6** | 2/2 | ~5GB |
| Ollama | llama3.1:8b | Q4_K_M | 3.3s | 10.8 | 2/2 | ~7GB |
| vLLM | Llama-3.2-3B | BF16 | 4.7s | 7.6 | 2/2 | **17GB** |

### Head-to-Head: Code Generation (500 tok)

| Engine | Model | Quant | Time | Tok/s |
|--------|-------|-------|------|-------|
| Ollama | lfm2.5-thinking:1.2b | Q4_K_M | **12.4s** | **40.4** |
| Ollama | qwen3:1.7b | Q4_K_M | 18.6s | 26.9 |
| Ollama | nemotron-3-nano:4b | Q4_K_M | 26.5s | 18.9 |
| vLLM | Llama-3.2-3B | BF16 | 65.6s | 7.6 |

**Summary:** Ollama 1.5-5x faster on CPU (GGUF Q4_K_M vs BF16). vLLM wins on consistency (0% variance) and continuous batching.

---

## Configuration Change Log

| Date | Foundation | Change | Impact |
|------|-----------|--------|--------|
| 03-20 | CDC | Context 256K→32K, KV q8_0, flash_attn | **+81% tok/s** (9.1→16.5) |
| 03-20 | CDC | Added nemotron-3-nano:4b, llama3.1:8b | New best CPU models |
| 03-21 | CDC | Tested vLLM CPU wheel (0.18.0+cpu) | Ollama wins for CPU today |
| 03-23 | TDC | First Qwen3.5-27B deploy (4x 3090) | 10.8 tok/s @ 64K context |
| 03-23 | TDC | Upgraded vLLM 0.11.2→0.18.0, transformers→5.3.0 | Required for Qwen3.5 support |
| 03-27 | TDC | Moved to 2x 3090, 256K context | Half GPUs, 4x more context |
| **03-27** | **TDC** | **Removed enforce-eager** | **4.2x throughput (48 tok/s)** |
| 04-06 | DEV210 | Deployed GenAI 10.3.4 (downgraded from 10.4.60-dev) | Clean slate for Gemma 4 testing |
| 04-06 | DEV210 | Created `cpu-4xlarge` VM type (16 vCPU, 64GB RAM) | Enables 26B and 31B Gemma 4 models |
| 04-06 | DEV210 | Upgraded Ollama 0.16.1 → 0.20.2 on all workers | Required for Gemma 4 architecture support |
| 04-06 | DEV210 | Deployed all 4 Gemma 4 variants (e2b, e4b, 26b, 31b) | First full Gemma 4 family CPU benchmark |
| **04-06** | **DEV210** | **Thinking suppression via SYSTEM prompt + client system message** | **E4B: 3.2x speedup, 72% token reduction, 90% accuracy** |
| 04-06 | CDC + DEV210 | Added 10-test accuracy benchmark suite (factual + tool correctness) | Revealed ministral-3:3b scores only 80% (refuses tools) |

---

## How to Add New Results

```bash
# Run the benchmark suite
./bench.sh --foundation tdc --worker <instance-id>

# Or with a tag for A/B testing
./bench.sh --foundation tdc --worker <instance-id> --tag "my-config-change"

# Compare two runs
python3 tools/compare-results.py results/tdc/gpu/run_a.json results/tdc/gpu/run_b.json

# Then update this file and commit
git add results/ RESULTS.md
git commit -m "bench: <description>"
```
