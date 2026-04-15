"""agentic grader: runs the task through 1-3 agent frameworks against a
seed git fixture. Returns per-framework results; the runner fans them out
into separate test rows.

test_def:
  fixture: str               # directory name under tests/agentic/fixtures/
  task_prompt: str           # what to tell the agent
  timeout_sec: int           # wall-clock per framework run
  frameworks: [str]          # subset of ["goose", "aider", "custom"]
  grader_config:
    setup_commands: [str]    # run in tempdir before agent (120s timeout)
    success_check:
      command: str           # shell command; exit 0 = full score
      max_diff_lines: int    # optional guardrail
    partial_credit: [{check: str, points: float}]  # independent checks
    cleanup: "always"        # only supported mode in v1
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from tools.agents import AgentRunResult
from tools.agents.aider_runner import run as aider_run
from tools.agents.custom_loop import run as custom_run
from tools.agents.goose_runner import run as goose_run
from tools.agents.opencode_runner import run as opencode_run
from tools.graders.base import GraderContext, GraderResult, register


def _copy_fixture(fixtures_dir: Path, fixture_name: str, dest: Path) -> None:
    """Copy fixture to dest, then rebuild .git/ from .git-seed/ if present."""
    src = fixtures_dir / fixture_name
    if not src.exists():
        raise FileNotFoundError(f"fixture not found: {src}")
    shutil.copytree(src, dest, dirs_exist_ok=True)
    seed = dest / ".git-seed"
    if seed.exists():
        # Rebuild a minimal .git/ from the seed: move .git-seed to .git,
        # then run `git init` which is idempotent and fills in the rest.
        git_dir = dest / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)
        seed.rename(git_dir)
        subprocess.run(["git", "init", "-q"], cwd=dest, check=False)


def _run_setup(commands: List[str], work: Path) -> bool:
    env = os.environ.copy()
    env["PYTHONPATH"] = "/var/vcap/packages/tanzubench/python-lib:" + \
                        "/var/vcap/packages/tanzubench:" + \
                        env.get("PYTHONPATH", "")
    for cmd in commands:
        r = subprocess.run(["bash", "-c", cmd], cwd=work,
                           capture_output=True, text=True, timeout=120,
                           env=env)
        if r.returncode != 0:
            # Tolerate pip install failures if all packages are importable
            # (happens on air-gapped BOSH VMs where deps are vendored)
            if "pip install" in cmd:
                # Extract package names: everything after "install" that
                # doesn't start with "-" is a package name
                parts = cmd.split()
                try:
                    idx = parts.index("install") + 1
                except ValueError:
                    return False
                # pip name → import name for common mismatches
                _IMPORT_MAP = {"pyyaml": "yaml", "pillow": "PIL",
                               "scikit-learn": "sklearn", "aider-chat": "aider"}
                pkgs = [p for p in parts[idx:] if not p.startswith("-")]
                all_ok = True
                for pkg in pkgs:
                    imp = _IMPORT_MAP.get(pkg.lower(), pkg)
                    chk = subprocess.run(
                        ["python3", "-c", f"import {imp}"],
                        capture_output=True, env=env)
                    if chk.returncode != 0:
                        all_ok = False
                        break
                if all_ok and pkgs:
                    continue
            return False
    return True


def _diff_lines(work: Path) -> int:
    r = subprocess.run(["git", "diff", "--stat"], cwd=work,
                       capture_output=True, text=True)
    # Last line of --stat is like " 3 files changed, 42 insertions(+), 5 deletions(-)"
    # Parse insertions + deletions.
    total = 0
    for line in r.stdout.splitlines():
        for part in line.split(","):
            part = part.strip()
            if "insertion" in part or "deletion" in part:
                try:
                    total += int(part.split()[0])
                except (ValueError, IndexError):
                    pass
    return total


def _score_framework_run(work: Path, run_result: AgentRunResult,
                         cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Compute score + details dict for one framework's run."""
    if run_result.status == "error":
        return {"score": 0.0, "status": "error",
                "details": {**asdict(run_result)}}

    # max_diff_lines guardrail
    success = cfg.get("success_check", {})
    max_diff = success.get("max_diff_lines")
    if max_diff is not None:
        diff = _diff_lines(work)
        if diff > max_diff:
            return {"score": 0.0, "status": "scored",
                    "details": {**asdict(run_result),
                                "rejected": "diff_too_large",
                                "diff_lines": diff}}

    if run_result.status == "timeout":
        # Try partial credit even on timeout.
        score = _partial_credit(work, cfg.get("partial_credit", []))
        return {"score": score, "status": "timeout",
                "details": {**asdict(run_result),
                            "partial_credit_score": score}}

    # Normal scored path: try success_check first.
    cmd = success.get("command")
    if cmd:
        r = subprocess.run(["bash", "-c", cmd], cwd=work,
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return {"score": 1.0, "status": "scored",
                    "details": {**asdict(run_result),
                                "success_check": "passed"}}

    # Fall through to partial credit.
    score = _partial_credit(work, cfg.get("partial_credit", []))
    return {"score": score, "status": "scored",
            "details": {**asdict(run_result),
                        "partial_credit_score": score}}


def _partial_credit(work: Path, checks: List[Dict[str, Any]]) -> float:
    """Independent checks: each awards its points iff its command exits 0."""
    score = 0.0
    for chk in checks:
        cmd = chk.get("check")
        pts = float(chk.get("points", 0.0))
        if not cmd:
            continue
        try:
            r = subprocess.run(["bash", "-c", cmd], cwd=work,
                               capture_output=True, timeout=60)
            if r.returncode == 0:
                score += pts
        except subprocess.TimeoutExpired:
            pass
    return min(1.0, score)


def grade_multi(test_def: Dict[str, Any], model_client: Any,
                ctx: GraderContext,
                model_url: str, model_name: str, api_key: str) -> List[GraderResult]:
    """Returns one GraderResult per framework. The runner fans these out."""
    cfg = test_def.get("grader_config") or {}
    frameworks = test_def.get("frameworks") or ["goose", "aider", "custom"]
    timeout = int(test_def.get("timeout_sec", 600))

    results: List[GraderResult] = []
    base_work = Path(ctx.work_dir) / f"agentic-{test_def['id']}"

    for fw in frameworks:
        fw_work = base_work / fw
        fw_work.parent.mkdir(parents=True, exist_ok=True)
        if fw_work.exists():
            shutil.rmtree(fw_work)
        try:
            _copy_fixture(Path(ctx.fixtures_dir), test_def["fixture"], fw_work)
        except Exception as e:
            results.append(GraderResult(
                score=0.0, status="error",
                details={"framework": fw, "error": f"fixture_setup_failed: {e}"},
            ))
            continue

        if not _run_setup(cfg.get("setup_commands", []), fw_work):
            results.append(GraderResult(
                score=0.0, status="error",
                details={"framework": fw, "error": "setup_commands failed"},
            ))
            if cfg.get("cleanup", "always") == "always":
                shutil.rmtree(fw_work, ignore_errors=True)
            continue

        task_prompt = test_def["task_prompt"]
        try:
            if fw == "custom":
                run_result = custom_run(task_prompt, fw_work, model_client, timeout)
            elif fw == "aider":
                run_result = aider_run(task_prompt, fw_work, model_url, model_name,
                                       api_key, timeout)
            elif fw == "goose":
                run_result = goose_run(task_prompt, fw_work, model_url, model_name,
                                       api_key, timeout)
            elif fw == "opencode":
                run_result = opencode_run(task_prompt, fw_work, model_url, model_name,
                                          api_key, timeout)
            else:
                run_result = AgentRunResult(status="error", elapsed_sec=0,
                                            turns_completed=0,
                                            error=f"unknown framework: {fw}")
        except Exception as e:
            run_result = AgentRunResult(status="error", elapsed_sec=0,
                                        turns_completed=0,
                                        error=f"{type(e).__name__}: {e}")

        scored = _score_framework_run(fw_work, run_result, cfg)
        results.append(GraderResult(
            score=scored["score"],
            status=scored["status"],
            details={"framework": fw, **scored["details"]},
        ))

        if cfg.get("cleanup", "always") == "always":
            shutil.rmtree(fw_work, ignore_errors=True)

    return results


@register("agentic")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    """Single-result entrypoint for registry compatibility.

    The runner should NOT call this directly — it should detect
    grader=="agentic" and call grade_multi() to fan out per-framework rows.
    This function exists so the registry stays consistent and returns an
    error if someone does try to grade an agentic test through the normal
    path.
    """
    return GraderResult(
        score=0.0, status="error",
        details={"error": "use grade_multi() for agentic grader, not grade()"},
    )
