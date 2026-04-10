"""needle grader: needle-in-haystack for long context.

test_def.grader_config:
  haystack_asset: str      # filename under tests/assets/
  needle: str              # unique phrase to inject
  depth: float             # 0.0-1.0, fractional position to inject needle
  question: str            # what to ask about the needle
  expected_answer: str     # what the response must contain

The grader loads the haystack, injects the needle at the given depth
(counted in characters), then prompts the model with haystack + question.
Score is 1.0 if expected_answer appears in response, else 0.0.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register


# Unicode dash/hyphen characters models like to emit when they think they're
# quoting a literal phrase. Normalize all of these to a plain ASCII hyphen
# before comparing so we're measuring "did the model retrieve the needle"
# rather than "did the model happen to emit the exact codepoints we used".
_DASH_CLASS = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2212\u00ad]")


def _normalize(s: str) -> str:
    """Lowercase, strip markdown emphasis markers, normalize unicode dashes,
    collapse runs of whitespace. Retains everything that matters for a
    substring lookup and strips everything that commonly varies across
    model outputs."""
    s = s.lower()
    s = _DASH_CLASS.sub("-", s)
    # Strip markdown bold/italic markers that often wrap the needle
    s = s.replace("**", "").replace("__", "").replace("*", "")
    # Collapse whitespace (newlines, double spaces, etc.)
    s = re.sub(r"\s+", " ", s)
    return s


@register("needle")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    asset_name = cfg["haystack_asset"]
    haystack_path = Path(ctx.assets_dir) / asset_name
    if not haystack_path.exists():
        return GraderResult(score=0.0, status="error",
                            details={"error": f"asset not found: {asset_name}"})
    haystack = haystack_path.read_text()
    depth = float(cfg.get("depth", 0.5))
    idx = int(len(haystack) * depth)
    needle = cfg["needle"]
    injected = haystack[:idx] + "\n\n" + needle + "\n\n" + haystack[idx:]

    prompt = f"{injected}\n\n{cfg['question']}"
    content, _, tokens, _ = model_client.chat(
        [{"role": "user", "content": prompt}]
    )
    response = content or ""
    expected = cfg["expected_answer"]
    matched = _normalize(expected) in _normalize(response)

    return GraderResult(
        score=1.0 if matched else 0.0,
        status="scored",
        details={
            "haystack_chars": len(haystack),
            "depth": depth,
            "needle": needle,
            "matched": matched,
        },
        raw_response=response,
    )
