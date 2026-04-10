"""file_check grader: prompt the model to write content; check filesystem.

test_def.grader_config:
  file_checks: list[dict]   # each: {path, must_exist, must_contain, forbidden_content}

The grader runs inside ctx.work_dir. The model's response is expected to
contain file contents that the runner writes out via explicit `write_file`
markers in the prompt template, OR the model uses tools. This grader
supports the simpler "content in response" path: the prompt asks for a
specific file's contents, and the grader writes the raw response to the
given path before running checks.

For this v1, behavior is:
  - Call the model with test_def.prompt
  - Write the raw response to grader_config.write_response_to
  - Run file_checks against ctx.work_dir

Score = fraction of checks that pass.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from tools.graders.base import GraderContext, GraderResult, register


def _run_checks(work_dir: Path, checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for chk in checks:
        path = work_dir / chk["path"]
        passed = True
        reasons = []
        if chk.get("must_exist") and not path.exists():
            passed = False
            reasons.append("does not exist")
        if chk.get("must_contain") and path.exists():
            text = path.read_text(errors="replace")
            for needle in chk["must_contain"]:
                if needle not in text:
                    passed = False
                    reasons.append(f"missing: {needle!r}")
        if chk.get("forbidden_content") and path.exists():
            text = path.read_text(errors="replace")
            for bad in chk["forbidden_content"]:
                if bad in text:
                    passed = False
                    reasons.append(f"forbidden present: {bad!r}")
        results.append({"path": chk["path"], "passed": passed, "reasons": reasons})
    return results


@register("file_check")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    checks = cfg.get("file_checks", [])
    if not checks:
        return GraderResult(score=0.0, status="error",
                            details={"error": "no file_checks configured"})

    content, _, _, _ = model_client.chat(
        [{"role": "user", "content": test_def["prompt"]}]
    )
    response = content or ""
    work = Path(ctx.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    write_to = cfg.get("write_response_to")
    if write_to:
        dest = work / write_to
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(response)

    check_results = _run_checks(work, checks)
    passed = sum(1 for r in check_results if r["passed"])
    total = len(check_results)
    score = passed / total if total else 0.0

    return GraderResult(
        score=score, status="scored",
        details={"checks": check_results, "passed": passed, "total": total},
        raw_response=response,
    )
