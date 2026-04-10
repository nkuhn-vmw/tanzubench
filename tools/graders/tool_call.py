"""tool_call grader: OpenAI function-calling correctness.

test_def.grader_config:
  tools: list[dict]                    # OpenAI tools schema to pass to model
  mode: "single" | "dual" | "restraint"
  expected_tool: str                   # for mode=single
  expected_param_key: str              # for mode=single
  expected_param_contains: str         # for mode=single
  expected_tools: list[str]            # for mode=dual (all must be called)
  expected_answer: str                 # optional, for mode=restraint

details:
  mode: str
  tool_calls: list[str]      # names of tools called
  matched: bool
  reason: str
"""
from __future__ import annotations

import json
from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register


def _arg_value(tc: Dict[str, Any], key: str) -> str:
    fn = tc.get("function", {})
    args = fn.get("arguments", "{}")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    return str(args.get(key, ""))


@register("tool_call")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    tools = cfg.get("tools", [])
    mode = cfg.get("mode", "single")

    content, tool_calls, _tokens, _elapsed = model_client.chat(
        [{"role": "user", "content": test_def["prompt"]}],
        tools=tools,
    )
    called_names = [tc.get("function", {}).get("name", "") for tc in (tool_calls or [])]
    base_details = {"mode": mode, "tool_calls": called_names}

    if mode == "single":
        if not tool_calls:
            return GraderResult(score=0.0, status="scored",
                                details={**base_details, "matched": False,
                                         "reason": "no tool called"},
                                raw_response=content)
        tc = tool_calls[0]
        name = tc.get("function", {}).get("name", "")
        if name != cfg["expected_tool"]:
            return GraderResult(score=0.0, status="scored",
                                details={**base_details, "matched": False,
                                         "reason": f"wrong tool: {name}"},
                                raw_response=content)
        val = _arg_value(tc, cfg["expected_param_key"])
        if cfg["expected_param_contains"].lower() not in val.lower():
            return GraderResult(score=0.0, status="scored",
                                details={**base_details, "matched": False,
                                         "reason": f"wrong param: {val}"},
                                raw_response=content)
        return GraderResult(score=1.0, status="scored",
                            details={**base_details, "matched": True},
                            raw_response=content)

    if mode == "dual":
        expected = set(cfg["expected_tools"])
        called = set(called_names)
        if expected.issubset(called):
            return GraderResult(score=1.0, status="scored",
                                details={**base_details, "matched": True},
                                raw_response=content)
        return GraderResult(score=0.0, status="scored",
                            details={**base_details, "matched": False,
                                     "missing": list(expected - called)},
                            raw_response=content)

    if mode == "restraint":
        if tool_calls:
            return GraderResult(score=0.0, status="scored",
                                details={**base_details, "matched": False,
                                         "reason": "called tool when none expected"},
                                raw_response=content)
        expected = cfg.get("expected_answer", "")
        if expected and expected.lower() not in (content or "").lower():
            # Restraint passed but answer missing — half credit.
            return GraderResult(score=0.5, status="scored",
                                details={**base_details, "matched": True,
                                         "reason": "restraint ok, answer missing"},
                                raw_response=content)
        return GraderResult(score=1.0, status="scored",
                            details={**base_details, "matched": True},
                            raw_response=content)

    return GraderResult(score=0.0, status="error",
                        details={"error": f"unknown mode: {mode}"})
