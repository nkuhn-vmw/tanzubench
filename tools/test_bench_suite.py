"""Unit tests for bench_suite aggregation + test loading logic.

Integration tests against a real model endpoint are out of scope — those
are exercised via the smoke-test task at the end of the plan.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import statistics

from tools.bench_suite import aggregate, slugify, resolve_assets  # noqa: E402


def test_aggregate_basic_category():
    rows = [
        {"id": "a", "category": "basic", "status": "scored", "score": 1.0,
         "agent_framework": None},
        {"id": "b", "category": "basic", "status": "scored", "score": 0.5,
         "agent_framework": None},
    ]
    agg = aggregate(rows, judge_configured=False)
    basic = next(c for c in agg["category_scores"] if c["category"] == "basic")
    assert basic["score"] == 0.75
    assert basic["status"] == "scored"


def test_aggregate_skipped_excluded_from_composite():
    rows = [
        {"id": "a", "category": "basic", "status": "scored", "score": 1.0,
         "agent_framework": None},
        {"id": "b", "category": "writing", "status": "skipped", "score": 0.0,
         "agent_framework": None},
    ]
    agg = aggregate(rows, judge_configured=False)
    assert agg["composite_over"] == 1  # only basic feeds composite
    writing = next(c for c in agg["category_scores"] if c["category"] == "writing")
    assert writing["status"] == "skipped"
    assert writing["score"] is None


def test_aggregate_agentic_averages_frameworks_per_task():
    rows = [
        {"id": "fix.aider", "category": "agentic", "status": "scored",
         "score": 1.0, "agent_framework": "aider"},
        {"id": "fix.opencode", "category": "agentic", "status": "scored",
         "score": 0.0, "agent_framework": "opencode"},
        {"id": "fix.custom", "category": "agentic", "status": "scored",
         "score": 0.5, "agent_framework": "custom"},
    ]
    agg = aggregate(rows, judge_configured=True)
    agentic = next(c for c in agg["category_scores"] if c["category"] == "agentic")
    assert abs(agentic["score"] - 0.5) < 0.001  # mean of 1.0, 0.0, 0.5


def test_aggregate_agent_framework_scores():
    rows = [
        {"id": "t1.aider", "category": "agentic", "status": "scored",
         "score": 1.0, "agent_framework": "aider"},
        {"id": "t2.aider", "category": "agentic", "status": "timeout",
         "score": 0.0, "agent_framework": "aider"},
    ]
    agg = aggregate(rows, judge_configured=False)
    fw = agg["agent_framework_scores"]
    assert len(fw) == 1
    assert fw[0]["framework"] == "aider"
    assert fw[0]["score"] == 0.5
    assert fw[0]["tasks"] == 2


def test_slugify():
    assert slugify("Qwen/Qwen3-32B-GPTQ-Int4") == "qwen-qwen3-32b-gptq-int4"
    assert slugify("meta-llama/Llama 3.1 8B") == "meta-llama-llama-3-1-8b"


def test_resolve_assets(tmp_path):
    (tmp_path / "haystack.txt").write_text("HAYSTACK_CONTENT")
    result = resolve_assets("before {{ asset:haystack.txt }} after", tmp_path)
    assert "HAYSTACK_CONTENT" in result
    assert "before" in result and "after" in result


def test_aggregate_per_category_throughput():
    """avg_tok_per_sec and avg_elapsed_ms should be computed for scored categories."""
    rows = [
        {"id": "a", "category": "basic", "status": "scored", "score": 1.0,
         "agent_framework": None, "completion_tokens": 10, "elapsed_ms": 1000},
        {"id": "b", "category": "basic", "status": "scored", "score": 0.5,
         "agent_framework": None, "completion_tokens": 20, "elapsed_ms": 2000},
    ]
    agg = aggregate(rows, judge_configured=False)
    basic = next(c for c in agg["category_scores"] if c["category"] == "basic")
    # row a: 10/1.0 = 10.0 tok/s; row b: 20/2.0 = 10.0 tok/s → avg = 10.0
    assert basic["avg_tok_per_sec"] == 10.0
    # avg elapsed: (1000 + 2000) / 2 = 1500
    assert basic["avg_elapsed_ms"] == 1500.0


def test_aggregate_throughput_none_when_no_tokens():
    """Categories with no token data should have null throughput."""
    rows = [
        {"id": "a", "category": "basic", "status": "scored", "score": 1.0,
         "agent_framework": None, "completion_tokens": None, "elapsed_ms": None},
    ]
    agg = aggregate(rows, judge_configured=False)
    basic = next(c for c in agg["category_scores"] if c["category"] == "basic")
    assert basic["avg_tok_per_sec"] is None
    assert basic["avg_elapsed_ms"] is None


def test_median_behavior():
    """Verify statistics.median gives expected values for multi-run logic."""
    scores = [0.5, 1.0, 0.75]
    assert statistics.median(scores) == 0.75
    elapsed = [100, 200, 150]
    assert statistics.median(elapsed) == 150


def test_aggregate_skipped_category_has_throughput_none():
    """Skipped categories always have null throughput fields."""
    rows = [
        {"id": "a", "category": "writing", "status": "skipped", "score": 0.0,
         "agent_framework": None},
    ]
    agg = aggregate(rows, judge_configured=False)
    writing = next(c for c in agg["category_scores"] if c["category"] == "writing")
    assert writing["status"] == "skipped"
    assert writing["avg_tok_per_sec"] is None
    assert writing["avg_elapsed_ms"] is None
