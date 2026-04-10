"""aider framework runner for the agentic grader.

Spawns `aider` in non-interactive mode pointed at the target model, waits
for completion or timeout, returns AgentRunResult. Scoring is done by the
agentic grader from filesystem state — this module only drives the process.

aider CLI reference (pinned via requirements.txt):
  aider --model openai/<model>
        --openai-api-base <url>
        --openai-api-key <key>
        --yes --no-auto-commits --no-stream
        --message "<task_prompt>"
        <file1> <file2> ...   (files to expose to aider)
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List

from tools.agents import AgentRunResult


def _aider_cmd() -> List[str]:
    """aider may be on PATH as a binary, OR installed as a Python module
    but not exposed as a binary (happens when pip puts it in
    ~/Library/Python/<ver>/bin on macOS and that dir isn't on PATH).
    Returns the command prefix, or None if aider isn't available at all.
    """
    if shutil.which("aider") is not None:
        return ["aider"]
    try:
        import aider.main  # noqa: F401
        return [sys.executable, "-m", "aider.main"]
    except ImportError:
        return []


def run(task_prompt: str, work_dir: Path, model_url: str, model_name: str,
        api_key: str, timeout_sec: int) -> AgentRunResult:
    prefix = _aider_cmd()
    if not prefix:
        return AgentRunResult(status="error", elapsed_sec=0.0, turns_completed=0,
                              error="aider not installed")

    # Expose all files in the fixture. Let aider decide which to edit.
    files = [str(p.relative_to(work_dir)) for p in work_dir.rglob("*")
             if p.is_file() and ".git" not in p.parts]

    # aider's --openai-api-base must include the /v1 suffix. Our bench
    # runner flag convention is that `model_url` is the base up to /v1
    # (e.g. http://host/v1) but many callers pass http://host:4000. Make
    # it work either way.
    base = model_url.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"

    cmd = [
        *prefix,
        "--model", f"openai/{model_name}",
        "--openai-api-base", base,
        "--openai-api-key", api_key or "dummy",
        "--yes", "--no-auto-commits", "--no-stream",
        "--no-pretty",
        "--no-show-model-warnings",
        "--no-gitignore",
        "--message", task_prompt,
        *files,
    ]

    start = time.time()
    try:
        proc = subprocess.Popen(
            cmd, cwd=work_dir,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, preexec_fn=os.setsid,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec)
            elapsed = time.time() - start
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            stdout, stderr = proc.communicate()
            return AgentRunResult(
                status="timeout", elapsed_sec=time.time() - start,
                turns_completed=_count_turns(stdout),
                stdout_excerpt=stdout[-500:] if stdout else "",
                stderr_excerpt=stderr[-500:] if stderr else "",
            )
    except FileNotFoundError:
        return AgentRunResult(status="error", elapsed_sec=0.0, turns_completed=0,
                              error="aider executable not found")

    return AgentRunResult(
        status="scored", elapsed_sec=elapsed,
        turns_completed=_count_turns(stdout),
        stdout_excerpt=stdout[-500:] if stdout else "",
        stderr_excerpt=stderr[-500:] if stderr else "",
    )


def _count_turns(stdout: str) -> int:
    """Best-effort turn count from aider's output.

    With --no-pretty --no-stream, aider does not emit the "> " prompt
    prefix that older parsers used. The most reliable per-turn signal
    in this mode is the "Tokens: <N> sent, <M> received." line which
    aider prints exactly once per LLM call. Each LLM call corresponds
    to one agent turn.
    """
    if not stdout:
        return 0
    # Count "Tokens: " lines — one per LLM call.
    n = stdout.count("Tokens: ")
    if n > 0:
        return n
    # Fallback for non-default aider modes that emit the chat prompt.
    return stdout.count("> ")
