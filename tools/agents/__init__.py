"""Agent harness adapters for the agentic grader.

Each module defines a `run(task_prompt, work_dir, model_url, model_name,
api_key, timeout_sec) -> AgentRunResult` function.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AgentRunResult:
    status: str              # "scored" | "timeout" | "error"
    elapsed_sec: float
    turns_completed: int
    last_tool_call: Optional[str] = None
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    error: Optional[str] = None
