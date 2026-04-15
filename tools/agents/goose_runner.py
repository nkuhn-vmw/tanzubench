"""goose framework runner for the agentic grader.

Drives Goose (https://github.com/block/goose) in non-interactive mode
against an OpenAI-compatible endpoint. Uses --provider openai with
OPENAI_HOST / OPENAI_API_KEY env vars for endpoint configuration.

Goose CLI flags used:
  --provider openai --model <name>
  --text <task_prompt>
  --no-session --no-profile --quiet
  --output-format json
  --with-builtin developer
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from tools.agents import AgentRunResult


def _count_turns(stdout: str) -> int:
    """Count agent turns from goose's JSON output.

    With --output-format json, goose emits a single JSON object with a
    messages array. Each assistant message containing a toolRequest counts
    as a turn (one LLM call that decided to use a tool).
    """
    if not stdout:
        return 0
    # Count toolRequest content blocks — each is one agent action
    count = stdout.count('"toolRequest"')
    if count > 0:
        return count
    # Fallback: count assistant messages (each is an LLM call)
    return stdout.count('"role":"assistant"')


def run(task_prompt: str, work_dir: Path, model_url: str, model_name: str,
        api_key: str, timeout_sec: int) -> AgentRunResult:
    goose_bin = shutil.which("goose")
    if goose_bin is None:
        # Check BOSH package path
        bosh_goose = "/var/vcap/packages/tanzubench/bin/goose"
        if os.path.isfile(bosh_goose) and os.access(bosh_goose, os.X_OK):
            goose_bin = bosh_goose
        else:
            return AgentRunResult(status="error", elapsed_sec=0.0,
                                  turns_completed=0,
                                  error="goose not installed")

    # OPENAI_HOST should be the base URL *without* /v1 — goose appends it.
    base = model_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]

    env = os.environ.copy()
    env["OPENAI_HOST"] = base
    env["OPENAI_API_KEY"] = api_key or "dummy"
    # Suppress goose telemetry and session persistence in benchmark context
    env["GOOSE_CLI_TELEMETRY"] = "false"
    env["DO_NOT_TRACK"] = "1"

    cmd = [
        goose_bin, "run",
        "--provider", "openai",
        "--model", model_name,
        "--text", task_prompt,
        "--no-session",
        "--no-profile",
        "--quiet",
        "--output-format", "json",
        "--with-builtin", "developer",
        "--max-turns", "20",
    ]

    start = time.time()
    try:
        proc = subprocess.Popen(
            cmd, cwd=work_dir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, preexec_fn=os.setsid,
            env=env,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec)
            elapsed = time.time() - start
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            stdout, stderr = proc.communicate()
            return AgentRunResult(
                status="timeout", elapsed_sec=time.time() - start,
                turns_completed=_count_turns(stdout or ""),
                stdout_excerpt=(stdout or "")[-500:],
                stderr_excerpt=(stderr or "")[-500:],
            )
    except FileNotFoundError:
        return AgentRunResult(status="error", elapsed_sec=0.0,
                              turns_completed=0,
                              error="goose executable not found")

    if proc.returncode != 0 and not (stdout or "").strip():
        return AgentRunResult(
            status="error", elapsed_sec=time.time() - start,
            turns_completed=0,
            error=f"goose exit {proc.returncode}: {(stderr or '')[-300:]}",
        )

    return AgentRunResult(
        status="scored", elapsed_sec=elapsed,
        turns_completed=_count_turns(stdout or ""),
        stdout_excerpt=(stdout or "")[-500:],
        stderr_excerpt=(stderr or "")[-500:],
    )
