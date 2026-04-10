"""contains grader: case-insensitive substring check.

test_def.grader_config:
  must_contain: list[str]  # all must be present
  must_not_contain: list[str]  # none may be present
"""
from __future__ import annotations

from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register


@register("contains")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    must = [s.lower() for s in cfg.get("must_contain", [])]
    must_not = [s.lower() for s in cfg.get("must_not_contain", [])]

    content, _, _, _ = model_client.chat(
        [{"role": "user", "content": test_def["prompt"]}]
    )
    response = content or ""
    lower = response.lower()
    missing = [s for s in must if s not in lower]
    forbidden = [s for s in must_not if s in lower]

    if not missing and not forbidden:
        return GraderResult(score=1.0, status="scored",
                            details={"missing": [], "forbidden": []},
                            raw_response=response)
    return GraderResult(
        score=0.0, status="scored",
        details={"missing": missing, "forbidden": forbidden},
        raw_response=response,
    )
