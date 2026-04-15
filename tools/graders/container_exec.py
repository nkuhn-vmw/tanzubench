"""container_exec grader: execute model's shell script in a Docker container
and verify system state.

test_def.grader_config:
  image: str                    # Docker image (e.g., ubuntu:22.04)
  setup_commands: list[str]     # commands to run before the model's script
  state_checks: list[dict]      # each has one of:
    - command: str, exit_code: int (default 0)
    - command: str, stdout_contains: str
    - file_exists: str

Docker not installed = all tests skipped.
Score = fraction of state_checks passing.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import uuid
from typing import Any, Dict, List

from tools.graders.base import GraderContext, GraderResult, register

_CODE_BLOCK = re.compile(r"```(?:bash|sh|shell)?\n(.*?)```", re.DOTALL)


def _extract_script(response: str) -> str:
    m = _CODE_BLOCK.search(response)
    if m:
        return m.group(1)
    return response


def _docker_exec(container: str, cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", container, "bash", "-c", cmd],
        capture_output=True, text=True, timeout=timeout
    )


def _run_checks(container: str, checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for chk in checks:
        if "file_exists" in chk:
            path = chk["file_exists"]
            try:
                r = _docker_exec(container, f"test -f {path} || test -d {path}")
                passed = r.returncode == 0
            except Exception:
                passed = False
            results.append({"type": "file_exists", "path": path, "passed": passed})

        elif "command" in chk:
            cmd = chk["command"]
            expected_exit = chk.get("exit_code", 0)
            stdout_contains = chk.get("stdout_contains")
            r = None
            try:
                r = _docker_exec(container, cmd)
                if stdout_contains:
                    passed = stdout_contains.lower() in (r.stdout + r.stderr).lower()
                else:
                    passed = r.returncode == expected_exit
            except Exception:
                passed = False
            results.append({"type": "command", "command": cmd, "passed": passed,
                            "stdout": (r.stdout[:200] if r is not None else "")})
        else:
            results.append({"type": "unknown", "passed": False})
    return results


def _local_exec(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True, text=True, timeout=timeout
    )


def _run_checks_local(checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run state checks directly on the local VM (fallback when Docker unavailable)."""
    results = []
    for chk in checks:
        if "file_exists" in chk:
            path = chk["file_exists"]
            try:
                r = _local_exec(f"test -f {path} || test -d {path}")
                passed = r.returncode == 0
            except Exception:
                passed = False
            results.append({"type": "file_exists", "path": path, "passed": passed})
        elif "command" in chk:
            cmd = chk["command"]
            expected_exit = chk.get("exit_code", 0)
            stdout_contains = chk.get("stdout_contains")
            r = None
            try:
                r = _local_exec(cmd)
                if stdout_contains:
                    passed = stdout_contains.lower() in (r.stdout + r.stderr).lower()
                else:
                    passed = r.returncode == expected_exit
            except Exception:
                passed = False
            results.append({"type": "command", "command": cmd, "passed": passed,
                            "stdout": (r.stdout[:200] if r is not None else "")})
        else:
            results.append({"type": "unknown", "passed": False})
    return results


def _grade_local(test_def: Dict[str, Any], model_client: Any,
                 ctx: GraderContext) -> GraderResult:
    """Fallback: run sysadmin tests directly on the VM without Docker."""
    cfg = test_def.get("grader_config") or {}
    prompt = test_def.get("prompt") or ""
    content, _, _, _ = model_client.chat([{"role": "user", "content": prompt}])
    response = content or ""
    script = _extract_script(response)

    try:
        for cmd in cfg.get("setup_commands", []):
            _local_exec(cmd, timeout=60)
        _local_exec(script, timeout=ctx.timeout_sec)
        checks = cfg.get("state_checks", [])
        check_results = _run_checks_local(checks)
        passed = sum(1 for c in check_results if c["passed"])
        total = len(check_results)
        score = passed / total if total > 0 else 0.0
        return GraderResult(
            score=round(score, 4), status="scored",
            details={"mode": "local", "checks": check_results,
                     "passed": passed, "total": total},
            raw_response=response,
        )
    except Exception as e:
        return GraderResult(score=0.0, status="error",
                            details={"mode": "local",
                                     "error": f"{type(e).__name__}: {e}"},
                            raw_response=response)


@register("container_exec")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    if not shutil.which("docker"):
        # Fall back to local execution on the VM
        return _grade_local(test_def, model_client, ctx)

    cfg = test_def.get("grader_config") or {}
    image = cfg.get("image", "ubuntu:22.04")

    prompt = test_def.get("prompt") or ""
    content, _, _, _ = model_client.chat([{"role": "user", "content": prompt}])
    response = content or ""
    script = _extract_script(response)

    container = f"tanzubench-{uuid.uuid4().hex[:8]}"
    try:
        # Start container
        subprocess.run(
            ["docker", "run", "-d", "--name", container, image, "sleep", "300"],
            capture_output=True, text=True, timeout=60, check=True
        )

        # Setup commands
        for cmd in cfg.get("setup_commands", []):
            _docker_exec(container, cmd, timeout=60)

        # Execute model's script
        _docker_exec(container, script, timeout=ctx.timeout_sec)

        # Run state checks
        checks = cfg.get("state_checks", [])
        check_results = _run_checks(container, checks)
        passed = sum(1 for c in check_results if c["passed"])
        total = len(check_results)
        score = passed / total if total > 0 else 0.0

        return GraderResult(
            score=round(score, 4), status="scored",
            details={"mode": "docker", "checks": check_results,
                     "passed": passed, "total": total},
            raw_response=response,
        )

    except subprocess.CalledProcessError as e:
        return GraderResult(score=0.0, status="error",
                            details={"error": f"docker failed: {e.stderr[:200]}"},
                            raw_response=response)
    except Exception as e:
        return GraderResult(score=0.0, status="error",
                            details={"error": f"{type(e).__name__}: {e}"},
                            raw_response=response)
    finally:
        subprocess.run(["docker", "rm", "-f", container],
                       capture_output=True, timeout=30)
