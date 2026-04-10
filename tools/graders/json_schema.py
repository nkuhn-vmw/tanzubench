"""json_schema grader: validate model output against a JSON Schema.

test_def.grader_config:
  schema: dict          # JSON Schema to validate against
  expected_values: dict  # optional dotpath → expected value map

details:
  parse_ok: bool
  extracted_json: dict | None
  schema_errors: list[str]
  schema_score: float
  content_matches: dict | None
  content_score: float | None
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from jsonschema import Draft202012Validator

from tools.graders.base import GraderContext, GraderResult, register

_JSON_BLOCK = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


def _extract_json(response: str) -> Optional[dict]:
    """Best-effort JSON extraction from model response."""
    # Try direct parse
    try:
        obj = json.loads(response)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    # Try markdown fences
    m = _JSON_BLOCK.search(response)
    if m:
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
    # Try first {...} substring
    start = response.find("{")
    if start >= 0:
        depth = 0
        for i, c in enumerate(response[start:], start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(response[start : i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break
    return None


def _resolve_dotpath(obj: Any, path: str) -> Any:
    """Resolve 'spec.containers[0].image' against a nested dict."""
    for part in re.split(r"\.|(?=\[)", path):
        if not part:
            continue
        m = re.match(r"\[(\d+)\]", part)
        if m:
            idx = int(m.group(1))
            if isinstance(obj, list) and idx < len(obj):
                obj = obj[idx]
            else:
                return None
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def _count_properties(schema: dict) -> int:
    """Rough count of leaf properties in a JSON Schema for scoring denominator."""
    count = 0
    props = schema.get("properties", {})
    for v in props.values():
        if v.get("type") == "object" or "properties" in v:
            count += _count_properties(v)
        elif v.get("type") == "array" and "items" in v:
            count += max(1, _count_properties(v["items"]))
        else:
            count += 1
    count += len(schema.get("required", []))
    return max(count, 1)


@register("json_schema")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    schema = cfg.get("schema")
    if not schema:
        return GraderResult(score=0.0, status="error",
                            details={"error": "missing grader_config.schema"})

    prompt = test_def.get("prompt") or test_def.get("prompt_template", "")
    content, _, _, _ = model_client.chat([{"role": "user", "content": prompt}])
    response = content or ""

    extracted = _extract_json(response)
    parse_ok = extracted is not None
    parse_score = 1.0 if parse_ok else 0.0

    # Schema validation
    schema_score = 0.0
    schema_errors = []
    if extracted is not None:
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(extracted), key=lambda e: list(e.path))
        # Count unique error paths to avoid cascading-error inflation
        unique_paths = set()
        for e in errors:
            path = ".".join(str(p) for p in e.absolute_path) or "<root>"
            unique_paths.add(path)
            schema_errors.append(f"{path}: {e.message}")
        total_props = _count_properties(schema)
        error_count = len(unique_paths)
        schema_score = max(0.0, 1.0 - (error_count / total_props))

    # Content validation (optional)
    expected = cfg.get("expected_values")
    content_score = None
    content_matches = None
    if expected and extracted is not None:
        content_matches = {}
        correct = 0
        for dotpath, exp_val in expected.items():
            actual = _resolve_dotpath(extracted, dotpath)
            match = str(actual).lower() == str(exp_val).lower()
            content_matches[dotpath] = match
            if match:
                correct += 1
        content_score = correct / len(expected) if expected else 0.0

    # Weighted score
    if content_score is not None:
        final = 0.3 * parse_score + 0.5 * schema_score + 0.2 * content_score
    else:
        final = 0.4 * parse_score + 0.6 * schema_score

    return GraderResult(
        score=round(max(0.0, min(1.0, final)), 4),
        status="scored",
        details={
            "parse_ok": parse_ok,
            "extracted_json": extracted,
            "schema_errors": schema_errors[:10],
            "schema_score": round(schema_score, 4),
            "content_matches": content_matches,
            "content_score": round(content_score, 4) if content_score is not None else None,
        },
        raw_response=response,
    )
