"""multi_turn grader: drives a scripted multi-turn conversation and
grades each turn against per-turn checks.

test_def.grader_config:
  turns: list of:
    user_message: str
    tools: list[dict] (optional, for tool-use turns)
    tool_result: dict (optional, injected before the model call)
    checks: list of:
      contains: str           # case-insensitive substring
      not_contains: str       # must NOT contain
      any_contains: list[str] # at least one must match
      tool_called: str        # tool call with this name present
      regex: str              # response matches pattern
      length_max: int         # word count <= N

Score = total checks passed / total checks across all turns.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from tools.graders.base import GraderContext, GraderResult, register


def _word_count(text: str) -> int:
    return len(text.split())


def _check(check: Dict[str, Any], content: str, tool_calls: list) -> Dict[str, Any]:
    """Evaluate one check against a response. Returns {type, value, passed, ...}."""
    if "contains" in check:
        val = check["contains"]
        passed = val.lower() in content.lower()
        return {"type": "contains", "value": val, "passed": passed}

    if "not_contains" in check:
        val = check["not_contains"]
        passed = val.lower() not in content.lower()
        return {"type": "not_contains", "value": val, "passed": passed}

    if "any_contains" in check:
        vals = check["any_contains"]
        low = content.lower()
        passed = any(v.lower() in low for v in vals)
        return {"type": "any_contains", "value": vals, "passed": passed,
                "matched": [v for v in vals if v.lower() in low]}

    if "tool_called" in check:
        name = check["tool_called"]
        called = [tc.get("function", {}).get("name", "") for tc in (tool_calls or [])]
        passed = name in called
        return {"type": "tool_called", "value": name, "passed": passed,
                "called": called}

    if "regex" in check:
        pattern = check["regex"]
        passed = bool(re.search(pattern, content, re.IGNORECASE | re.DOTALL))
        return {"type": "regex", "value": pattern, "passed": passed}

    if "length_max" in check:
        limit = int(check["length_max"])
        actual = _word_count(content)
        passed = actual <= limit
        return {"type": "length_max", "value": limit, "passed": passed,
                "actual": actual}

    return {"type": "unknown", "passed": False}


@register("multi_turn")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    turns = cfg.get("turns", [])
    if not turns:
        return GraderResult(score=0.0, status="error",
                            details={"error": "no turns defined"})

    messages: List[Dict[str, Any]] = []
    turn_details = []
    total_passed = 0
    total_checks = 0

    for turn in turns:
        # Inject canned tool result if present (for multi-step tool tests)
        if "tool_result" in turn:
            tr = turn["tool_result"]
            messages.append({
                "role": "tool",
                "tool_call_id": tr.get("tool_call_id", "call_0"),
                "content": tr.get("content", ""),
            })

        # Add user message
        messages.append({"role": "user", "content": turn["user_message"]})

        # Call model
        tools = turn.get("tools")
        try:
            content, tool_calls, _, _ = model_client.chat(messages, tools=tools)
        except Exception as e:
            content = f"ERROR: {e}"
            tool_calls = []

        # Build assistant message for history
        assistant_msg = {"role": "assistant", "content": content or ""}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        # Grade checks for this turn
        checks_results = []
        for chk in turn.get("checks", []):
            result = _check(chk, content or "", tool_calls or [])
            checks_results.append(result)
            total_checks += 1
            if result["passed"]:
                total_passed += 1

        turn_passed = sum(1 for c in checks_results if c["passed"])
        turn_details.append({
            "user": turn["user_message"][:200],
            "response": (content or "")[:300],
            "checks": checks_results,
            "passed": turn_passed,
            "total": len(checks_results),
        })

    score = total_passed / total_checks if total_checks > 0 else 0.0

    return GraderResult(
        score=round(score, 4),
        status="scored",
        details={
            "turns": turn_details,
            "total_passed": total_passed,
            "total_checks": total_checks,
        },
        raw_response=None,  # multi-turn has no single response
    )
