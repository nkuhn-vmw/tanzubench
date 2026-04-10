# Judge Endpoint Setup

The `reasoning`, `writing`, and `research` test categories use an LLM judge to score model responses against a rubric. This document covers what the judge must expose, the reference TDC deployment, runner flags, and troubleshooting.

---

## What a judge endpoint must expose

The judge must be an OpenAI-compatible `/v1/chat/completions` endpoint that:

- Accepts `messages`, `temperature`, and `response_format` in the POST body.
- Honors `temperature=0.0` for deterministic grading.
- Supports `response_format={"type": "json_object"}` to force JSON output (or at minimum returns a parseable JSON object without it — the runner falls back to best-effort JSON extraction).
- Returns responses quickly enough for the `judge_max_retries` retry budget (default 2 retries, each up to the test's `timeout_sec`).

Any model capable of following structured grading rubrics will work. Qwen3-32B has been used as the reference judge on TDC.

---

## Reference deployment: Qwen3-32B on TDC via vLLM

The reference judge runs on the TDC foundation (2x RTX 3090) via vLLM, exposed on a stable internal URL.

**Prerequisites:** BOSH access to your GPU foundation. Credentials are in your OpsManager credentials store.

**vLLM launch args used for the judge:**

```bash
python3 -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3-32B-GPTQ-Int4 \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 2 \
  --max-model-len 32768 \
  --enforce-eager \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

The `--enforce-eager` flag disables CUDA graph caching — this trades throughput for stability, appropriate for a judge that serves low-QPS grading traffic. Omit it if you need higher throughput.

The judge endpoint is then proxied through the GenAI tile or exposed directly. The runner accepts either a bare `http://host:port` or a full base URL ending in `/v1`.

---

## Pointing the runner at the judge

Three flags and one optional environment variable:

```bash
python3 tools/bench_suite.py \
  --url http://model-endpoint/v1 \
  --model "Qwen3-32B-GPTQ-Int4" \
  --foundation tdc --hardware gpu \
  --judge-url http://<judge-endpoint>/v1 \
  --judge-model "Qwen3-32B" \
  --judge-api-key "$JUDGE_KEY"
```

| Flag              | Env var equivalent | Notes |
|-------------------|--------------------|-------|
| `--judge-url`     | none               | Base URL of the judge endpoint. |
| `--judge-model`   | none               | Model name as the judge endpoint knows it. |
| `--judge-api-key` | none               | API key; pass empty string if the endpoint is unauthenticated. |

If `--judge-url` is omitted, all `llm_judge` tests are skipped (score 0.0, excluded from denominator). The composite score is computed over the categories that ran.

The runner probes the judge with a minimal chat request before starting. If the probe fails, the runner logs a warning and proceeds without a judge (same as omitting `--judge-url`).

---

## Moving the judge to another foundation

When you switch the judge endpoint — different host, different model, or different foundation — update all three flags. The runner records these fields in the result JSON under `grading`:

```json
"grading": {
  "judge_configured": true,
  "judge_model": "Qwen3-32B",
  "judge_endpoint": "http://<judge-endpoint>/v1",
  "judge_fingerprint": "sha256:abcd1234...",
  "judge_run_date": "2026-04-08T..."
}
```

`judge_fingerprint` is a SHA-256 hash of the judge URL (used as a stable opaque identifier). Results graded by different judges — even the same model at a different URL — have different fingerprints. The leaderboard uses this to flag when comparisons cross judge boundaries; don't mix results from different fingerprints without noting it.

**What changes on a new foundation:**
- `--judge-url` — new host/port.
- `--judge-model` — may differ if the model name differs on the new engine.
- `--judge-api-key` — new credential if the endpoint uses one.
- `judge_fingerprint` in the result — changes automatically based on the new URL.

**What does not change:** the rubrics in test YAML files, the scoring logic in `llm_judge.py`, or any result fields outside `grading`.

---

## Troubleshooting

**Judge probe fails at startup**

The runner logs `[judge] probe failed — treating as not configured` and continues without a judge. Check:
- Is the judge endpoint reachable from where you're running the runner?
- Does `curl -s http://<judge-url>/v1/models` return 200?
- Is the API key correct?

**JSON parse errors from judge**

Logged as `status=error` with `judge_parse_failure=true` in `details.judge`. The judge returned something that isn't valid JSON. Common causes:
- Model is generating reasoning tokens before the JSON (thinking-token issue — add a suppression system message to `llm_judge.py`'s `judge_prompt`).
- Model ignores `response_format=json_object` — check vLLM version, not all versions support this flag for all models.
- Judge rubric instructions are ambiguous — tighten the "Return ONLY valid JSON" instructions.

The `judge_max_retries` config key (default 2) retries with an appended reminder. Increase it for flakey models.

**Temperature not honored**

Some models or engines ignore `temperature=0.0`. This makes judge scores non-deterministic. Verify by calling the judge with `temperature=0.0` twice against the same input and comparing `judge_raw`. If scores differ, either the engine doesn't honor temperature or the model has minimum-temperature constraints.

**Judge is slow, tests time out**

Judge calls happen after the model call, within the test's `timeout_sec`. For judge-graded tests, `timeout_sec` should be set high enough to cover both model inference and judge inference. 120–180 seconds is a reasonable floor for complex reasoning prompts.

**Result has `judge_configured: false` but I passed `--judge-url`**

The probe failed — see "Judge probe fails at startup" above. Check the runner's stderr for the probe error message.
