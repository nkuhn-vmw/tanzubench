"""exec_build grader: model fixes a broken config, grader runs the build.

test_def.grader_config:
  target_file: str           # filename to write model's response to
  build_command: str          # shell command to run (must exit 0 for full score)
  build_tool: str             # tool name to check availability (npm, docker, go, mvn, python3)
  partial_credit: list[dict]  # optional [{check: str, points: float}]

Score: 1.0 if build exits 0, else sum partial_credit checks, else 0.0.
Missing build tool = status: skipped.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register

_CODE_BLOCK = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


def _extract_content(response: str) -> str:
    m = _CODE_BLOCK.search(response)
    if m:
        return m.group(1)
    return response


@register("exec_build")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    target_file = cfg.get("target_file")
    build_cmd = cfg.get("build_command")
    build_tool = cfg.get("build_tool", "python3")

    if not target_file or not build_cmd:
        return GraderResult(score=0.0, status="error",
                            details={"error": "missing target_file or build_command"})

    # Check tool availability
    tool_bin = build_tool.split()[0]
    if not shutil.which(tool_bin):
        return GraderResult(score=0.0, status="skipped",
                            details={"error": f"build tool not available: {tool_bin}"})

    prompt = test_def.get("prompt") or ""
    content, _, _, _ = model_client.chat([{"role": "user", "content": prompt}])
    response = content or ""
    fixed = _extract_content(response)

    work = Path(ctx.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    # Write any seed files from grader_config.seed_files
    for sf in cfg.get("seed_files", []):
        p = work / sf["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(sf["content"])

    # Write model's fix
    dest = work / target_file
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(fixed)

    # Run build
    try:
        r = subprocess.run(
            ["bash", "-c", build_cmd], cwd=work,
            capture_output=True, text=True, timeout=60
        )
        build_ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        return GraderResult(score=0.0, status="timeout",
                            details={"error": "build timed out"}, raw_response=response)

    if build_ok:
        return GraderResult(score=1.0, status="scored",
                            details={"build_ok": True, "stdout": r.stdout[:500]},
                            raw_response=response)

    # Partial credit
    score = 0.0
    for chk in cfg.get("partial_credit", []):
        cmd = chk.get("check")
        pts = float(chk.get("points", 0))
        if cmd:
            try:
                cr = subprocess.run(["bash", "-c", cmd], cwd=work,
                                    capture_output=True, timeout=30)
                if cr.returncode == 0:
                    score += pts
            except Exception:
                pass

    return GraderResult(score=min(1.0, score), status="scored",
                        details={"build_ok": False, "stderr": r.stderr[:500]},
                        raw_response=response)
