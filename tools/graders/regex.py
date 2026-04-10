"""regex grader: re.search pattern + optional must_not_match list.

test_def.grader_config:
  pattern: str
  flags: list[str]          # "IGNORECASE", "MULTILINE", "DOTALL"
  must_not_match: list[str] # patterns that cause failure if they match
"""
from __future__ import annotations

import re
from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register

_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
}


@register("regex")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    pattern = cfg.get("pattern")
    if not pattern:
        return GraderResult(score=0.0, status="error",
                            details={"error": "missing grader_config.pattern"})

    flags = 0
    for f in cfg.get("flags", []):
        flags |= _FLAG_MAP.get(f, 0)

    content, _, _, _ = model_client.chat(
        [{"role": "user", "content": test_def["prompt"]}]
    )
    response = content or ""

    if not re.search(pattern, response, flags):
        return GraderResult(score=0.0, status="scored",
                            details={"pattern": pattern, "matched": False},
                            raw_response=response)

    for neg in cfg.get("must_not_match", []):
        if re.search(neg, response, flags):
            return GraderResult(score=0.0, status="scored",
                                details={"pattern": pattern, "matched": True,
                                         "violated_must_not": neg},
                                raw_response=response)

    return GraderResult(score=1.0, status="scored",
                        details={"pattern": pattern, "matched": True},
                        raw_response=response)
