#!/usr/bin/env python3
"""Single canonical benchmark runner. Loads YAML test definitions, runs
each through its grader, aggregates category + composite scores, writes a
v2 result JSON.

Usage: see docs/test-suite.md or `python3 tools/bench_suite.py --help`
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import signal
import statistics
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("ERROR: jsonschema required. pip install jsonschema", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.graders import get_grader, GraderContext, GraderResult  # noqa: E402
from tools.graders.agentic import grade_multi as agentic_grade_multi  # noqa: E402


CATEGORY_ORDER = [
    "basic", "tool_use", "structured_output", "instruction", "file_ops",
    "coding", "debugging", "long_context", "multi_turn",
    "reasoning", "writing", "research", "agentic",
]


# ----- OpenAI-compatible model client ------------------------------------

THINK_SUPPRESS_SYSTEM = (
    "You are a helpful assistant. Use tools when needed. "
    "Respond directly and concisely without extended reasoning."
)


class ModelClient:
    """Thin wrapper over requests.post to OpenAI-compatible /v1/chat/completions.

    Returns (content, tool_calls, completion_tokens, elapsed_sec) from .chat().

    suppress_thinking: when True, prepends a system message instructing the
    model to skip reasoning tokens. Critical for Gemma 4 / Qwen3 on CPU —
    without it, thinking tokens dominate latency (see README). If the caller
    already provided a system message as messages[0], it's left alone (we
    don't stack system messages).
    """
    def __init__(self, url: str, model: str, api_key: str,
                 suppress_thinking: bool = False):
        self.url = url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.suppress_thinking = suppress_thinking
        # Rolling stats from the most recent chat() — the runner reads these
        # after each grader call so it can record them on the test row.
        # Graders don't need to know about token counting.
        self.last_completion_tokens: int = 0
        self.last_prompt_tokens: int = 0
        self.last_elapsed_sec: float = 0.0

    def chat(self, messages, tools=None, temperature=None, response_format=None):
        import urllib.request
        if self.suppress_thinking and (not messages or messages[0].get("role") != "system"):
            messages = [{"role": "system", "content": THINK_SUPPRESS_SYSTEM}] + list(messages)
        payload = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
        if temperature is not None:
            payload["temperature"] = temperature
        if response_format is not None:
            payload["response_format"] = response_format
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.url}/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                body = json.loads(resp.read())
        except Exception as e:
            return (f"ERROR: {type(e).__name__}: {e}", [], 0, time.time() - start)
        elapsed = time.time() - start
        self.last_elapsed_sec = elapsed
        choices = body.get("choices", [])
        if not choices:
            self.last_completion_tokens = 0
            self.last_prompt_tokens = 0
            return ("", [], 0, elapsed)
        msg = choices[0].get("message", {})
        # Ollama's OpenAI-compat mode sometimes splits reasoning output from
        # content (e.g. message.reasoning vs message.content). When thinking
        # is suppressed this doesn't happen, but fall back to reasoning if
        # content is empty so graders still see *something* to score.
        content = (msg.get("content") or msg.get("reasoning") or "") or ""
        tool_calls = msg.get("tool_calls", []) or []
        usage = body.get("usage") or {}
        self.last_completion_tokens = int(usage.get("completion_tokens") or 0)
        self.last_prompt_tokens = int(usage.get("prompt_tokens") or 0)
        return (content, tool_calls, self.last_completion_tokens, elapsed)


# ----- Engine config introspection ---------------------------------------

def probe_engine_config(url: str, engine_name: str, api_key: str) -> Dict[str, Any]:
    """Query the engine's metadata endpoint and return settings.

    vLLM: GET /v1/models → returns model list with settings.
    Ollama: POST /api/show → returns modelfile + parameters.
    Unknown: return a minimal stub.
    """
    import urllib.request
    try:
        if engine_name == "vllm":
            req = urllib.request.Request(
                f"{url.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            return {"_source": "vllm:/v1/models", **data}
        if engine_name == "ollama":
            # Ollama's /api/show expects {"name": "<model>"} — we don't know
            # model here; runner will call this after the first chat. For
            # now, return list.
            req = urllib.request.Request(
                f"{url.rstrip('/')}/api/tags",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            return {"_source": "ollama:/api/tags", **data}
    except Exception as e:
        return {"_error": f"metadata unreachable: {type(e).__name__}: {e}"}
    return {"_source": "unknown"}


# ----- Test loading ------------------------------------------------------

_ASSET_RE = re.compile(r"\{\{\s*asset:([^\s}]+)\s*\}\}")


def resolve_assets(text: str, assets_dir: Path) -> str:
    def _repl(m):
        p = assets_dir / m.group(1)
        if not p.exists():
            return f"[missing asset: {m.group(1)}]"
        return p.read_text()
    return _ASSET_RE.sub(_repl, text)


def load_tests(tests_dir: Path, assets_dir: Path,
               schema_validator: Draft202012Validator,
               category_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Walk tests_dir, load + validate every .yaml file, resolve asset substitutions."""
    tests = []
    errors = []
    for yaml_path in sorted(tests_dir.rglob("*.yaml")):
        if "fixtures" in yaml_path.parts or "assets" in yaml_path.parts:
            continue  # fixtures are referenced, not loaded as tests
        try:
            raw = yaml.safe_load(yaml_path.read_text())
        except yaml.YAMLError as e:
            errors.append(f"{yaml_path}: YAML parse error: {e}")
            continue
        if not isinstance(raw, dict):
            errors.append(f"{yaml_path}: not a dict")
            continue
        val_errs = sorted(schema_validator.iter_errors(raw),
                          key=lambda e: list(e.path))
        if val_errs:
            for e in val_errs:
                loc = ".".join(str(p) for p in e.absolute_path) or "<root>"
                errors.append(f"{yaml_path}: {loc}: {e.message}")
            continue
        # Filename must match id
        if raw["id"] != yaml_path.stem:
            errors.append(f"{yaml_path}: id {raw['id']!r} does not match filename")
            continue
        # Resolve {{asset:...}} substitutions in prompt fields.
        for fld in ("prompt", "prompt_template", "task_prompt"):
            if fld in raw and isinstance(raw[fld], str):
                raw[fld] = resolve_assets(raw[fld], assets_dir)
        if category_filter and raw["category"] not in category_filter:
            continue
        tests.append(raw)
    if errors:
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        raise ValueError(f"{len(errors)} test definition error(s); aborting")
    return tests


# ----- Runner core -------------------------------------------------------

@dataclass
class RunConfig:
    url: str
    api_key: str
    model: str
    engine: str
    foundation: str
    hardware: str
    gpu_count: int
    gpu_model: Optional[str]
    judge_url: Optional[str]
    judge_model: Optional[str]
    judge_api_key: Optional[str]
    suppress_thinking: bool
    categories: Optional[List[str]]
    tests_dir: Path
    output_dir: Path
    tag: Optional[str]
    no_interactive: bool
    runs: int = 1
    max_run_time: int = 7200       # total wall-clock cap for the entire run (seconds)
    task_timeout: Optional[int] = None  # per-test cap; overrides YAML timeout_sec when lower


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()


def _effective_timeout(test_def: Dict[str, Any], cfg: RunConfig) -> int:
    """Compute the effective per-test timeout: the lesser of the YAML's
    timeout_sec and the CLI's --task-timeout (if set). This lets GPU runs
    use generous YAML budgets while CPU runs cap every test to e.g. 120s
    via one flag, with the same YAML files."""
    yaml_timeout = int(test_def.get("timeout_sec", 60))
    if cfg.task_timeout is not None:
        return min(yaml_timeout, cfg.task_timeout)
    return yaml_timeout


def run_test(test_def: Dict[str, Any], cfg: RunConfig, ctx: GraderContext,
             model_client: ModelClient) -> List[Dict[str, Any]]:
    """Run one test. Returns 1 row for most graders, N rows for agentic."""
    start = time.time()
    test_id = test_def["id"]
    category = test_def["category"]
    grader_name = test_def["grader"]

    def _row(score, status, details, prompt_tokens=0, completion_tokens=0,
             elapsed_ms=0, agent_fw=None, raw=None, judge=None):
        tps = None
        if completion_tokens and elapsed_ms and elapsed_ms > 0:
            tps = round(completion_tokens / (elapsed_ms / 1000.0), 2)
        return {
            "id": test_id if agent_fw is None else f"{test_id}.{agent_fw}",
            "name": test_def["name"],
            "category": category,
            "grader": grader_name,
            "score": round(score, 4),
            "max_score": float(test_def.get("max_score", 1.0)),
            "status": status,
            "agent_framework": agent_fw,
            "prompt_tokens": prompt_tokens or None,
            "completion_tokens": completion_tokens or None,
            "elapsed_ms": elapsed_ms or None,
            "tok_per_sec": tps,
            "details": details or {},
            "judge": judge,
            "raw_response": (raw or "")[:2000] if raw else None,
            "notes": None,
        }

    # Agentic fans out to N rows.
    if grader_name == "agentic":
        results = agentic_grade_multi(
            test_def, model_client, ctx,
            cfg.url, cfg.model, cfg.api_key,
        )
        rows = []
        for r in results:
            fw = (r.details or {}).get("framework")
            rows.append(_row(r.score, r.status, r.details,
                             elapsed_ms=int((r.details.get("elapsed_sec") or 0) * 1000),
                             agent_fw=fw))
        return rows

    # Normal path.
    grader_fn = get_grader(grader_name)
    n_runs = max(1, min(5, cfg.runs))  # clamp 1..5

    if n_runs > 1:
        # Multi-run: repeat the grader N times, use median score + elapsed.
        # Agentic tests always run once because each framework invocation is
        # an independent benchmark dimension; repeating and taking the median
        # would collapse that meaningful variance into a single number.
        run_scores: List[float] = []
        run_elapsed: List[int] = []
        run_completion_tokens: List[int] = []
        last_result = None
        for _ in range(n_runs):
            model_client.last_completion_tokens = 0
            model_client.last_prompt_tokens = 0
            t_run = time.time()
            try:
                r = grader_fn(test_def, model_client, ctx)
            except Exception as e:
                return [_row(0.0, "error", {"exception": f"{type(e).__name__}: {e}"})]
            run_scores.append(r.score)
            run_elapsed.append(int((time.time() - t_run) * 1000))
            run_completion_tokens.append(model_client.last_completion_tokens)
            last_result = r
        med_score = statistics.median(run_scores)
        med_elapsed = int(statistics.median(run_elapsed))
        med_tokens = int(statistics.median(run_completion_tokens))
        details = dict(last_result.details or {})
        details["run_scores"] = run_scores
        details["run_elapsed_ms"] = run_elapsed
        details["p95_elapsed_ms"] = max(run_elapsed)  # for N≤5 p95≈max
        budget_ms = _effective_timeout(test_def, cfg) * 1000
        if last_result.status == "scored" and med_elapsed > budget_ms:
            details.update({
                "budget_ms": budget_ms,
                "overrun_ms": med_elapsed - budget_ms,
                "original_score": round(med_score, 4),
                "overrun_reason": "median elapsed exceeded usability budget",
            })
            return [_row(0.0, "timeout", details,
                         prompt_tokens=model_client.last_prompt_tokens,
                         completion_tokens=med_tokens,
                         elapsed_ms=med_elapsed, raw=last_result.raw_response)]
        return [_row(med_score, last_result.status, details,
                     prompt_tokens=model_client.last_prompt_tokens,
                     completion_tokens=med_tokens,
                     elapsed_ms=med_elapsed, raw=last_result.raw_response,
                     judge=(details.get("judge") if "judge" in details else None))]

    # Single-run path (default).
    model_client.last_completion_tokens = 0
    model_client.last_prompt_tokens = 0
    try:
        result = grader_fn(test_def, model_client, ctx)
    except Exception as e:
        return [_row(0.0, "error", {"exception": f"{type(e).__name__}: {e}"})]
    elapsed_ms = int((time.time() - start) * 1000)

    # USABILITY BUDGET: effective timeout (min of YAML + CLI --task-timeout)
    # is the human-tolerable wait for this test. If the grader returned a
    # valid score but took longer than the budget, we override to timeout
    # with score=0. This makes the benchmark honest about CPU-vs-GPU
    # practicality rather than just "eventual correctness".
    budget_ms = _effective_timeout(test_def, cfg) * 1000
    if result.status == "scored" and elapsed_ms > budget_ms:
        overrun = {
            **(result.details or {}),
            "budget_ms": budget_ms,
            "overrun_ms": elapsed_ms - budget_ms,
            "original_score": round(result.score, 4),
            "overrun_reason": "completed but exceeded usability budget",
        }
        return [_row(0.0, "timeout", overrun,
                     prompt_tokens=model_client.last_prompt_tokens,
                     completion_tokens=model_client.last_completion_tokens,
                     elapsed_ms=elapsed_ms, raw=result.raw_response)]
    return [_row(result.score, result.status, result.details,
                 prompt_tokens=model_client.last_prompt_tokens,
                 completion_tokens=model_client.last_completion_tokens,
                 elapsed_ms=elapsed_ms, raw=result.raw_response,
                 judge=(result.details.get("judge") if "judge" in (result.details or {}) else None))]


def aggregate(test_rows: List[Dict[str, Any]], judge_configured: bool) -> Dict[str, Any]:
    """Compute category_scores, composite_score, agent_framework_scores."""
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for row in test_rows:
        by_cat.setdefault(row["category"], []).append(row)

    category_scores = []
    scored_cat_scores = []
    for cat in CATEGORY_ORDER:
        rows = by_cat.get(cat, [])
        if not rows:
            category_scores.append({
                "category": cat, "score": None, "max": 1.0,
                "tasks": 0, "status": "skipped",
                "avg_tok_per_sec": None, "avg_elapsed_ms": None,
            })
            continue
        # Skipped rows excluded from denominator.
        scored = [r for r in rows if r["status"] in ("scored", "timeout")]
        skipped = [r for r in rows if r["status"] == "skipped"]
        errors = [r for r in rows if r["status"] == "error"]
        if not scored and not errors and skipped:
            category_scores.append({
                "category": cat, "score": None, "max": 1.0,
                "tasks": len(rows), "status": "skipped",
                "avg_tok_per_sec": None, "avg_elapsed_ms": None,
            })
            continue
        if cat == "agentic":
            # Average of (mean of frameworks per task) across tasks.
            by_task: Dict[str, List[float]] = {}
            for r in scored + errors:
                # "id" is "<task>.<framework>"; strip framework.
                task_id = r["id"].rsplit(".", 1)[0]
                by_task.setdefault(task_id, []).append(r["score"])
            if by_task:
                per_task_means = [sum(s) / len(s) for s in by_task.values()]
                cat_score = sum(per_task_means) / len(per_task_means)
            else:
                cat_score = 0.0
        else:
            counted = scored + errors
            cat_score = (sum(r["score"] for r in counted) / len(counted)
                         if counted else 0.0)

        # Per-category throughput: mean tok/s and mean elapsed across rows
        # that have both completion_tokens and elapsed_ms populated.
        tps_rows = [r for r in (scored + errors)
                    if r.get("completion_tokens") and r.get("elapsed_ms")]
        if tps_rows:
            avg_tps = round(
                sum(r["completion_tokens"] / (r["elapsed_ms"] / 1000.0)
                    for r in tps_rows) / len(tps_rows),
                2,
            )
            avg_elapsed = round(
                sum(r["elapsed_ms"] for r in tps_rows) / len(tps_rows),
                1,
            )
        else:
            avg_tps = None
            avg_elapsed = None

        category_scores.append({
            "category": cat, "score": round(cat_score, 4), "max": 1.0,
            "tasks": len(rows), "status": "scored",
            "avg_tok_per_sec": avg_tps, "avg_elapsed_ms": avg_elapsed,
        })
        scored_cat_scores.append(cat_score)

    composite = (sum(scored_cat_scores) / len(scored_cat_scores)
                 if scored_cat_scores else 0.0)

    # Agent framework breakdown.
    agent_rows = by_cat.get("agentic", [])
    agent_fw_scores = None
    if agent_rows:
        by_fw: Dict[str, List[float]] = {}
        for r in agent_rows:
            fw = r.get("agent_framework")
            if fw:
                by_fw.setdefault(fw, []).append(r["score"])
        agent_fw_scores = [
            {"framework": fw, "score": round(sum(s) / len(s), 4), "tasks": len(s)}
            for fw, s in by_fw.items()
        ]

    return {
        "category_scores": category_scores,
        "composite_score": round(composite, 4),
        "composite_max": 1.0,
        "composite_over": len(scored_cat_scores),
        "agent_framework_scores": agent_fw_scores,
    }


def judge_fingerprint(endpoint: Optional[str]) -> Optional[str]:
    if not endpoint:
        return None
    return "sha256:" + hashlib.sha256(endpoint.encode()).hexdigest()[:16]


def probe_judge(judge_client: Optional[ModelClient]) -> bool:
    if judge_client is None:
        return False
    try:
        content, _, _, _ = judge_client.chat(
            [{"role": "user", "content": "Respond with OK"}],
        )
        return bool(content)
    except Exception:
        return False


def run(cfg: RunConfig) -> Path:
    # Load tests.
    schema_v = Draft202012Validator(
        json.loads((REPO_ROOT / "schema" / "test-v1.schema.json").read_text())
    )
    tests = load_tests(cfg.tests_dir, cfg.tests_dir / "assets", schema_v, cfg.categories)
    print(f"[load] {len(tests)} tests across "
          f"{len({t['category'] for t in tests})} categories")

    # Clients.
    model_client = ModelClient(cfg.url, cfg.model, cfg.api_key,
                                suppress_thinking=cfg.suppress_thinking)
    judge_client = None
    if cfg.judge_url and cfg.judge_model:
        judge_client = ModelClient(cfg.judge_url, cfg.judge_model,
                                   cfg.judge_api_key or "")
    judge_ok = probe_judge(judge_client)
    if judge_client and not judge_ok:
        print("[judge] probe failed — treating as not configured")
        judge_client = None

    # Warm up the target. Ollama cold-loads a model on its first call which
    # can take 20-60s for mid-sized models. Without a warmup, the first test
    # absorbs that latency and frequently times out. This warmup call is
    # intentionally NOT scored and NOT counted toward the test budget.
    print("[warmup] target …", end="", flush=True)
    t0 = time.time()
    try:
        content, _, _, _ = model_client.chat(
            [{"role": "user", "content": "hi"}]
        )
        print(f" ok ({time.time() - t0:.1f}s)")
    except Exception as e:
        print(f" WARN: {e} (continuing)")

    # Engine config probe.
    engine_config = probe_engine_config(cfg.url, cfg.engine, cfg.api_key)

    # Output path + in-progress file.
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    stem = f"{slugify(cfg.model)}-{ts}"
    final_path = cfg.output_dir / f"{stem}.json"
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    in_progress = cfg.output_dir / f".in-progress-{stem}.json"

    # Context for graders.
    work_dir = REPO_ROOT / ".bench-work" / stem
    work_dir.mkdir(parents=True, exist_ok=True)
    ctx = GraderContext(
        model_client=model_client,
        judge_client=judge_client,
        work_dir=work_dir,
        assets_dir=cfg.tests_dir / "assets",
        fixtures_dir=cfg.tests_dir / "agentic" / "fixtures",
        timeout_sec=60,
    )

    # Run tests, sorted by CATEGORY_ORDER.
    tests_sorted = sorted(tests,
                          key=lambda t: (CATEGORY_ORDER.index(t["category"])
                                         if t["category"] in CATEGORY_ORDER else 99,
                                         t["id"]))
    test_rows: List[Dict[str, Any]] = []
    current_cat = None
    run_start = time.time()

    def _save_in_progress():
        in_progress.write_text(json.dumps({"tests": test_rows}, indent=2))

    def _time_capped_row(t: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Produce a score-0 timeout row for a test that was never started
        (run hit --max-run-time) or couldn't finish."""
        return {
            "id": t["id"], "name": t["name"], "category": t["category"],
            "grader": t["grader"], "score": 0.0, "max_score": 1.0,
            "status": "timeout", "agent_framework": None,
            "prompt_tokens": None, "completion_tokens": None,
            "elapsed_ms": None, "tok_per_sec": None,
            "details": {"reason": reason}, "judge": None,
            "raw_response": None, "notes": None,
        }

    for t in tests_sorted:
        # ── MAX RUN TIME CHECK ──────────────────────────────────────
        # If the total wall-clock exceeds --max-run-time, score ALL
        # remaining tests as timeout/0 and stop. This is what makes
        # CPU vs GPU composites comparable: CPU models that run out of
        # time get honest zeros on the categories they couldn't reach.
        elapsed_total = time.time() - run_start
        if elapsed_total > cfg.max_run_time:
            remaining = [t2 for t2 in tests_sorted
                         if not any(r["id"] == t2["id"] or
                                    r["id"].startswith(t2["id"] + ".")
                                    for r in test_rows)]
            if remaining:
                mins = int(elapsed_total / 60)
                print(f"\n[time cap] {mins}m elapsed > {cfg.max_run_time // 60}m limit. "
                      f"Scoring {len(remaining)} remaining tests as timeout/0.")
                for rem in remaining:
                    if rem["grader"] == "agentic":
                        # Agentic fans out per-framework
                        for fw in rem.get("frameworks", ["aider", "custom"]):
                            test_rows.append({
                                **_time_capped_row(rem, "run_time_cap_exceeded"),
                                "id": f"{rem['id']}.{fw}",
                                "agent_framework": fw,
                            })
                    else:
                        test_rows.append(_time_capped_row(rem, "run_time_cap_exceeded"))
            break

        if t["category"] != current_cat:
            if current_cat is not None:
                _save_in_progress()
            current_cat = t["category"]
            print(f"[category] {current_cat}")

        eff_timeout = _effective_timeout(t, cfg)
        ctx.timeout_sec = eff_timeout
        t_start = time.time()
        print(f"  [test] {t['id']} (budget {eff_timeout}s) ...", end="", flush=True)
        try:
            def _timeout_handler(signum, frame):
                raise TimeoutError(f"hard kill after {eff_timeout * 3}s")
            if sys.platform != "win32":
                signal.signal(signal.SIGALRM, _timeout_handler)
                hardkill = max(eff_timeout * 3, 120)
                signal.alarm(hardkill)
            rows = run_test(t, cfg, ctx, model_client)
        except TimeoutError as e:
            rows = [{
                **_time_capped_row(t, str(e)),
                "elapsed_ms": int((time.time() - t_start) * 1000),
            }]
        finally:
            if sys.platform != "win32":
                signal.alarm(0)
        test_rows.extend(rows)
        mark = "PASS" if rows[0]["status"] == "scored" and rows[0]["score"] >= 0.5 else rows[0]["status"].upper()
        print(f" {mark} ({rows[0]['score']:.2f})")

        # Early-abort rule.
        if (t["category"] == "basic" and
            sum(1 for r in test_rows if r["category"] == "basic" and r["score"] >= 0.5) * 2
                < len([r for r in test_rows if r["category"] == "basic"])):
            if not cfg.no_interactive:
                resp = input("basic category scoring <50%. continue? [y/N] ")
                if resp.strip().lower() != "y":
                    print("aborted.")
                    sys.exit(1)

    # Aggregate.
    agg = aggregate(test_rows, judge_configured=(judge_client is not None))

    # Determine skipped categories: those that had all-skipped rows.
    skipped_cats = [cs["category"] for cs in agg["category_scores"]
                    if cs["status"] == "skipped"]

    # Assemble final result.
    result = {
        "schema_version": "2.0.0",
        "result_type": "suite",
        "meta": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "foundation": cfg.foundation,
            "tile_version": None,
            "tag": cfg.tag,
            "notes": None,
            "source_file": None,
        },
        "target": {
            "name": cfg.model,
            "display_name": None, "family": None,
            "parameters_b": None, "active_parameters_b": None,
            "architecture": None, "quant": None, "size_gb": None,
        },
        "engine": {
            "name": cfg.engine,
            "version": None,
            "config": engine_config,
        },
        "hardware": {
            "vm_type": None, "cpu": None, "cpu_cores": None, "ram_gb": None,
            "gpu_count": cfg.gpu_count,
            "gpu_model": cfg.gpu_model,
            "gpu_memory_gb": None, "power_limit_watts": None,
        },
        "grading": {
            "judge_configured": judge_client is not None,
            "judge_model": cfg.judge_model if judge_client else None,
            "judge_endpoint": cfg.judge_url if judge_client else None,
            "judge_fingerprint": judge_fingerprint(cfg.judge_url) if judge_client else None,
            "judge_run_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if judge_client else None,
            "skipped_categories": skipped_cats,
        },
        "tests": test_rows,
        "summary": {
            "headline_metric": "composite_score",
            "headline_value": agg["composite_score"],
            "headline_unit": None,
            "composite_score": agg["composite_score"],
            "composite_max": agg["composite_max"],
            "composite_over": agg["composite_over"],
            "total_tokens": sum((r["completion_tokens"] or 0) for r in test_rows),
            "total_time_ms": sum((r["elapsed_ms"] or 0) for r in test_rows),
            "category_scores": agg["category_scores"],
            "agent_framework_scores": agg["agent_framework_scores"],
        },
    }

    # Validate before write.
    result_schema = Draft202012Validator(
        json.loads((REPO_ROOT / "schema" / "result-v2.schema.json").read_text())
    )
    errs = sorted(result_schema.iter_errors(result), key=lambda e: list(e.path))
    if errs:
        bad_path = cfg.output_dir / f"{stem}.invalid.json"
        bad_path.write_text(json.dumps(result, indent=2))
        print(f"ERROR: result did not validate; wrote to {bad_path}", file=sys.stderr)
        for e in errs:
            loc = ".".join(str(p) for p in e.absolute_path) or "<root>"
            print(f"  {loc}: {e.message}", file=sys.stderr)
        sys.exit(1)

    final_path.write_text(json.dumps(result, indent=2))
    if in_progress.exists():
        in_progress.unlink()
    print(f"[done] wrote {final_path}  composite={agg['composite_score']:.3f}")
    return final_path


def main() -> int:
    p = argparse.ArgumentParser(description="GenAI benchmark suite runner")
    p.add_argument("--url", required=True, help="target model endpoint, e.g. http://x/v1")
    p.add_argument("--api-key", default="", help="target model API key")
    p.add_argument("--model", required=True)
    p.add_argument("--engine", choices=["vllm", "ollama", "other"], default="vllm")
    p.add_argument("--foundation", required=True)
    p.add_argument("--hardware", choices=["cpu", "gpu"], required=True)
    p.add_argument("--gpu-count", type=int, default=0)
    p.add_argument("--gpu-model", default=None)
    p.add_argument("--judge-url", default=None)
    p.add_argument("--judge-model", default=None)
    p.add_argument("--judge-api-key", default=None)
    p.add_argument("--suppress-thinking", action="store_true",
                   help="prepend a system message suppressing reasoning "
                        "tokens (critical for Gemma 4 / Qwen3 on CPU)")
    p.add_argument("--categories", default=None,
                   help="comma-separated category filter; default=all")
    p.add_argument("--tests-dir", default=str(REPO_ROOT / "tests"))
    p.add_argument("--output", default=None,
                   help="output directory; default results/<foundation>/<hw>/")
    p.add_argument("--tag", default=None)
    p.add_argument("--no-interactive", action="store_true")
    p.add_argument("--runs", type=int, default=1, metavar="N",
                   help="repeat each non-agentic test N times (1–5) and record "
                        "median score + elapsed; default 1 (unchanged behavior)")
    p.add_argument("--max-run-time", type=int, default=7200,
                   help="total wall-clock cap in seconds; remaining tests score 0 "
                        "when exceeded (default 7200 = 2 hours)")
    p.add_argument("--task-timeout", type=int, default=None,
                   help="per-test timeout cap in seconds; overrides each test's "
                        "YAML timeout_sec when lower. Use for CPU runs: "
                        "--task-timeout 120 caps every test at 2 minutes")
    args = p.parse_args()

    output = Path(args.output) if args.output else \
        REPO_ROOT / "results" / args.foundation / args.hardware

    cfg = RunConfig(
        url=args.url, api_key=args.api_key, model=args.model,
        engine=args.engine, foundation=args.foundation, hardware=args.hardware,
        gpu_count=args.gpu_count, gpu_model=args.gpu_model,
        judge_url=args.judge_url, judge_model=args.judge_model,
        judge_api_key=args.judge_api_key,
        suppress_thinking=args.suppress_thinking,
        categories=args.categories.split(",") if args.categories else None,
        tests_dir=Path(args.tests_dir), output_dir=output,
        tag=args.tag, no_interactive=args.no_interactive,
        runs=max(1, min(5, args.runs)),
        max_run_time=args.max_run_time,
        task_timeout=args.task_timeout,
    )
    run(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
