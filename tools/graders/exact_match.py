"""exact_match grader: normalized string equality against expected_answer.

test_def.grader_config:
  expected_answer: str    # required
  case_sensitive: bool    # default false
  strip: bool             # default true

details:
  expected: str
  got: str
  matched: bool
"""
from __future__ import annotations

from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register


@register("exact_match")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    expected = cfg.get("expected_answer")
    if expected is None:
        return GraderResult(score=0.0, status="error",
                            details={"error": "missing grader_config.expected_answer"})

    prompt = test_def["prompt"]
    content, _tool_calls, _tokens, _elapsed = model_client.chat(
        [{"role": "user", "content": prompt}]
    )
    response = content or ""
    cand = response.strip() if cfg.get("strip", True) else response
    exp = expected.strip() if cfg.get("strip", True) else expected

    if not cfg.get("case_sensitive", False):
        cand = cand.lower()
        exp = exp.lower()

    matched = cand == exp
    return GraderResult(
        score=1.0 if matched else 0.0,
        status="scored",
        details={"expected": expected, "got": response[:200], "matched": matched},
        raw_response=response,
    )
