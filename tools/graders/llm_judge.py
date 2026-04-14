"""llm_judge grader: calls an external judge model to grade the response.

test_def.prompt (or prompt_template with {{asset:...}} resolved upstream)
test_def.grader_config:
  judge_rubric: str            # prompt for the judge, should ask for JSON output
  judge_aggregation: "mean" | "weighted"
  judge_weights: dict          # required if aggregation="weighted"
  judge_temperature: float     # default 0.0
  judge_max_retries: int       # default 2

If ctx.judge_client is None, test is skipped with status="skipped".
Judge is called with temperature=0.0, response_format=json_object if
supported. Response must be valid JSON with numeric rubric fields.

details.judge:
  model_response: the candidate response being graded
  rubric_scores: {dimension: float}
  rationale: str
  judge_raw: str (raw judge output for audit)
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json(text: str) -> Dict[str, Any]:
    """Best-effort JSON parse — try direct, then first {...} substring."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_RE.search(text)
    if m:
        return json.loads(m.group(0))
    raise ValueError("no JSON object found in judge response")


def _aggregate(rubric: Dict[str, float], mode: str, weights: Dict[str, float] | None) -> float:
    numeric = {k: float(v) for k, v in rubric.items() if k != "rationale"
               and isinstance(v, (int, float))}
    if not numeric:
        return 0.0
    if mode == "weighted" and weights:
        total_w = sum(weights.get(k, 0) for k in numeric)
        if total_w == 0:
            return 0.0
        return sum(numeric[k] * weights.get(k, 0) for k in numeric) / total_w
    return sum(numeric.values()) / len(numeric)


@register("llm_judge")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    if ctx.judge_client is None:
        return GraderResult(score=0.0, status="skipped",
                            details={"reason": "no judge configured"})

    cfg = test_def.get("grader_config") or {}
    rubric = cfg.get("judge_rubric")
    if not rubric:
        return GraderResult(score=0.0, status="error",
                            details={"error": "missing grader_config.judge_rubric"})

    # Use prompt_template (asset substitutions resolved by runner upstream)
    # or plain prompt.
    prompt = test_def.get("prompt") or test_def.get("prompt_template", "")
    content, _, _, _ = model_client.chat([{"role": "user", "content": prompt}])
    candidate = content or ""

    judge_prompt = (
        "You are a strict grader. Return ONLY valid JSON.\n\n"
        f"ORIGINAL INSTRUCTION:\n{prompt}\n\n"
        f"CANDIDATE RESPONSE:\n{candidate}\n\n"
        f"RUBRIC:\n{rubric}\n"
    )

    max_retries = int(cfg.get("judge_max_retries", 2))
    temperature = float(cfg.get("judge_temperature", 0.0))

    last_err = None
    judge_raw = ""
    parsed = None
    for attempt in range(max_retries + 1):
        try:
            jc_content, _, _, _ = ctx.judge_client.chat(
                [{"role": "user", "content": judge_prompt}],
                temperature=temperature,
                # response_format omitted — many endpoints (ollama, some proxies)
                # return 422. The rubric prompt already requests JSON output.
            )
            judge_raw = jc_content or ""
            parsed = _parse_json(judge_raw)
            break
        except (ValueError, json.JSONDecodeError) as e:
            last_err = str(e)
            judge_prompt += "\n\nYour last response was not valid JSON. Return ONLY a JSON object."
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            break

    if parsed is None:
        return GraderResult(
            score=0.0, status="error",
            details={"judge": {"model_response": candidate[:500],
                               "judge_parse_failure": True,
                               "error": last_err, "judge_raw": judge_raw[:500]}},
            raw_response=candidate,
        )

    score = _aggregate(parsed, cfg.get("judge_aggregation", "mean"),
                       cfg.get("judge_weights"))
    score = max(0.0, min(1.0, score))
    rubric_scores = {k: v for k, v in parsed.items() if k != "rationale"
                     and isinstance(v, (int, float))}

    return GraderResult(
        score=score, status="scored",
        details={"judge": {
            "model_response": candidate[:500],
            "rubric_scores": rubric_scores,
            "rationale": parsed.get("rationale", ""),
            "judge_raw": judge_raw[:500],
        }},
        raw_response=candidate,
    )
