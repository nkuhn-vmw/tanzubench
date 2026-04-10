"""opencode framework runner for the agentic grader.

Implementation strategy: opencode's `run` subcommand doesn't accept an
inline --api-base or --api-key, but it reads provider configuration from
~/.config/opencode/opencode.json at startup. We temporarily overwrite
that file with a single-provider config pointing at the test target,
invoke opencode, then restore the original on completion (success or
failure).

Concurrency caveat: this mutates a user-global file. Tests run
sequentially in bench_suite.py so there's no in-process race, but if
something else on the same machine is using opencode at the same time,
they'll clash. Acceptable for a benchmark runner.

Safety: the original config is always restored via a try/finally.
A copy is also left at ~/.config/opencode/opencode.json.bench-backup
until the restore succeeds, so an aborted run is recoverable.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from tools.agents import AgentRunResult


OPENCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.json"
BACKUP = OPENCODE_CONFIG.with_suffix(".json.bench-backup")


def _build_config(model_url: str, model_name: str, api_key: str) -> dict:
    base = model_url.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            "bench": {
                "name": "bench-target",
                "npm": "@ai-sdk/openai-compatible",
                "models": {model_name: {"name": model_name}},
                "options": {
                    "baseURL": base,
                    "apiKey": api_key or "dummy",
                },
            }
        },
    }


@contextmanager
def _swapped_config(model_url: str, model_name: str, api_key: str):
    """Backup → overwrite → yield → restore. Safe under exception."""
    OPENCODE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    had_original = OPENCODE_CONFIG.exists()
    if had_original:
        shutil.copy(OPENCODE_CONFIG, BACKUP)
    try:
        OPENCODE_CONFIG.write_text(
            json.dumps(_build_config(model_url, model_name, api_key), indent=2)
        )
        yield
    finally:
        if had_original and BACKUP.exists():
            shutil.copy(BACKUP, OPENCODE_CONFIG)
            BACKUP.unlink()
        elif not had_original and OPENCODE_CONFIG.exists():
            OPENCODE_CONFIG.unlink()


def _count_turns(stdout: str) -> int:
    """Count agent turns from opencode's --format json event stream.

    opencode emits one JSON event per line. We count `step-finish` (or
    `step_finish`) events — each step is a single LLM call from the
    agent's POV, which is the closest analogue to a "turn" across
    frameworks. Falls back to counting `step-start` if no finish events
    were emitted (e.g. truncated stream after a timeout).
    """
    if not stdout:
        return 0
    # opencode varies between hyphen and underscore in its event names
    # depending on version, so accept both.
    finish = stdout.count('"type":"step-finish"') + stdout.count('"type":"step_finish"')
    if finish > 0:
        return finish
    start_evt = stdout.count('"type":"step-start"') + stdout.count('"type":"step_start"')
    return start_evt


def run(task_prompt: str, work_dir: Path, model_url: str, model_name: str,
        api_key: str, timeout_sec: int) -> AgentRunResult:
    if shutil.which("opencode") is None:
        return AgentRunResult(status="error", elapsed_sec=0.0, turns_completed=0,
                              error="opencode not installed")

    start = time.time()
    try:
        with _swapped_config(model_url, model_name, api_key):
            cmd = [
                "opencode", "run",
                "-m", f"bench/{model_name}",
                "--format", "json",
                "--dir", str(work_dir),
                task_prompt,
            ]
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
                        turns_completed=_count_turns(stdout or ""),
                        stdout_excerpt=(stdout or "")[-500:],
                        stderr_excerpt=(stderr or "")[-500:],
                    )
            except FileNotFoundError:
                return AgentRunResult(status="error", elapsed_sec=0.0,
                                      turns_completed=0,
                                      error="opencode executable not found")
    except Exception as e:
        return AgentRunResult(status="error", elapsed_sec=time.time() - start,
                              turns_completed=0,
                              error=f"config swap failed: {type(e).__name__}: {e}")

    return AgentRunResult(
        status="scored", elapsed_sec=elapsed,
        turns_completed=_count_turns(stdout or ""),
        stdout_excerpt=(stdout or "")[-500:],
        stderr_excerpt=(stderr or "")[-500:],
    )
