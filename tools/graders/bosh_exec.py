"""bosh_exec grader: execute model's shell script on a disposable BOSH VM.

For tile deployments where Docker isn't available, this grader uses the
BOSH director to spin up a disposable Ubuntu VM, execute the model's
shell commands, verify system state, and destroy the VM.

Requires BOSH CLI on PATH and BOSH_ENVIRONMENT, BOSH_CLIENT,
BOSH_CLIENT_SECRET env vars set. Falls back to container_exec (Docker)
or skips if neither is available.

test_def.grader_config:
  image: str                    # ignored for BOSH (always ubuntu-jammy)
  setup_commands: list[str]     # commands to run before the model's script
  state_checks: list[dict]      # same as container_exec

Score = fraction of state_checks passing.
"""
from __future__ import annotations

import os
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




def _run_checks_local(checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run state checks directly on the local machine."""
    import subprocess
    results = []
    for chk in checks:
        if "file_exists" in chk:
            path = chk["file_exists"]
            import os
            passed = os.path.exists(path)
            results.append({"type": "file_exists", "path": path, "passed": passed})
        elif "command" in chk:
            cmd = chk["command"]
            expected_exit = chk.get("exit_code", 0)
            stdout_contains = chk.get("stdout_contains")
            try:
                r = subprocess.run(["bash", "-c", cmd],
                                   capture_output=True, text=True, timeout=30)
                stdout = r.stdout + r.stderr
                if stdout_contains:
                    passed = stdout_contains.lower() in stdout.lower()
                else:
                    passed = r.returncode == expected_exit
            except Exception:
                passed = False
                stdout = ""
            results.append({"type": "command", "command": cmd, "passed": passed,
                            "stdout": stdout[:200] if stdout else ""})
        else:
            results.append({"type": "unknown", "passed": False})
    return results


def _grade_local(test_def, model_client, ctx, response, script, cfg):
    """Run sysadmin test directly on the local machine.
    Used on BOSH errand VMs which are ephemeral Ubuntu VMs with root."""
    import subprocess
    # Run setup commands
    for cmd in cfg.get("setup_commands", []):
        subprocess.run(["bash", "-c", cmd],
                       capture_output=True, text=True, timeout=120)
    # Execute model script
    subprocess.run(["bash", "-c", script],
                   capture_output=True, text=True, timeout=ctx.timeout_sec)
    # Check state
    checks = cfg.get("state_checks", [])
    check_results = _run_checks_local(checks)
    passed = sum(1 for c in check_results if c["passed"])
    total = len(check_results)
    score = passed / total if total > 0 else 0.0
    return GraderResult(
        score=round(score, 4), status="scored",
        details={"checks": check_results, "passed": passed, "total": total,
                  "method": "local_vm"},
        raw_response=response,
    )

def _has_bosh() -> bool:
    """Check if BOSH CLI + director credentials are available."""
    return (shutil.which("bosh") is not None and
            os.environ.get("BOSH_ENVIRONMENT") is not None)


def _has_docker() -> bool:
    return shutil.which("docker") is not None


def _run_checks_ssh(deployment: str, instance: str,
                     checks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run state checks via bosh ssh."""
    results = []
    for chk in checks:
        if "file_exists" in chk:
            path = chk["file_exists"]
            try:
                r = subprocess.run(
                    ["bosh", "-d", deployment, "-n", "ssh", instance, "-c",
                     f"test -f {path} || test -d {path}"],
                    capture_output=True, text=True, timeout=30
                )
                passed = r.returncode == 0
            except Exception:
                passed = False
            results.append({"type": "file_exists", "path": path, "passed": passed})

        elif "command" in chk:
            cmd = chk["command"]
            expected_exit = chk.get("exit_code", 0)
            stdout_contains = chk.get("stdout_contains")
            try:
                r = subprocess.run(
                    ["bosh", "-d", deployment, "-n", "ssh", instance, "-c", cmd],
                    capture_output=True, text=True, timeout=30
                )
                stdout = r.stdout
                if stdout_contains:
                    passed = stdout_contains.lower() in stdout.lower()
                else:
                    passed = r.returncode == expected_exit
            except Exception:
                passed = False
                stdout = ""
            results.append({"type": "command", "command": cmd, "passed": passed,
                            "stdout": stdout[:200] if stdout else ""})
        else:
            results.append({"type": "unknown", "passed": False})
    return results


@register("bosh_exec")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    # Try Docker first (faster), fall back to BOSH
    if _has_docker():
        from tools.graders.container_exec import grade as docker_grade
        return docker_grade.__wrapped__(test_def, model_client, ctx) if hasattr(docker_grade, '__wrapped__') else docker_grade(test_def, model_client, ctx)

    if not _has_bosh():
        # Fallback: run directly on the local VM (safe for ephemeral errand VMs)
        return _grade_local(test_def, model_client, ctx, response, script, cfg)

    cfg = test_def.get("grader_config") or {}
    prompt = test_def.get("prompt") or ""
    content, _, _, _ = model_client.chat([{"role": "user", "content": prompt}])
    response = content or ""
    script = _extract_script(response)

    deployment = f"tanzubench-sysadmin-{uuid.uuid4().hex[:6]}"
    instance = "test-vm/0"

    try:
        # Deploy a minimal single-VM deployment
        manifest = f"""---
name: {deployment}
releases: []
stemcells:
  - alias: default
    os: ubuntu-jammy
    version: latest
instance_groups:
  - name: test-vm
    instances: 1
    azs: [az1]
    vm_type: default
    stemcell: default
    networks:
      - name: default
update:
  canaries: 1
  max_in_flight: 1
  canary_watch_time: 1000-30000
  update_watch_time: 1000-30000
"""
        manifest_path = f"/tmp/{deployment}.yml"
        with open(manifest_path, "w") as f:
            f.write(manifest)

        # Deploy
        r = subprocess.run(
            ["bosh", "-d", deployment, "-n", "deploy", manifest_path],
            capture_output=True, text=True, timeout=300
        )
        if r.returncode != 0:
            return GraderResult(score=0.0, status="error",
                                details={"error": f"bosh deploy failed: {r.stderr[:200]}"},
                                raw_response=response)

        # Run setup commands
        for cmd in cfg.get("setup_commands", []):
            subprocess.run(
                ["bosh", "-d", deployment, "-n", "ssh", instance, "-c", cmd],
                capture_output=True, text=True, timeout=120
            )

        # Execute model's script
        subprocess.run(
            ["bosh", "-d", deployment, "-n", "ssh", instance, "-c", script],
            capture_output=True, text=True, timeout=ctx.timeout_sec
        )

        # Run state checks
        checks = cfg.get("state_checks", [])
        check_results = _run_checks_ssh(deployment, instance, checks)
        passed = sum(1 for c in check_results if c["passed"])
        total = len(check_results)
        score = passed / total if total > 0 else 0.0

        return GraderResult(
            score=round(score, 4), status="scored",
            details={"checks": check_results, "passed": passed, "total": total,
                      "method": "bosh_vm"},
            raw_response=response,
        )

    except Exception as e:
        return GraderResult(score=0.0, status="error",
                            details={"error": f"{type(e).__name__}: {e}"},
                            raw_response=response)
    finally:
        # Always clean up
        subprocess.run(
            ["bosh", "-d", deployment, "-n", "delete-deployment", "--force"],
            capture_output=True, timeout=120
        )
        try:
            os.remove(manifest_path)
        except Exception:
            pass
