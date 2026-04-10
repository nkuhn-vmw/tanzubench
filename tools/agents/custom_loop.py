"""Minimal in-process agent loop for the agentic grader baseline.

Tool schema: read_file, write_file, list_dir, run_bash, done.
System prompt instructs the model to operate on files under work_dir and
call `done` when finished. Max 20 turns. Returns AgentRunResult.

This is a baseline control — when aider and opencode disagree on a model,
the custom loop isolates model quality from framework quirks.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from tools.agents import AgentRunResult

MAX_TURNS = 20

TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read the contents of a file relative to the working directory.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write content to a file relative to the working directory. Overwrites.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "List entries in a directory relative to the working directory.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "run_bash",
        "description": "Run a bash command in the working directory. Returns stdout+stderr.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "done",
        "description": "Signal that the task is complete. Call this when finished.",
        "parameters": {"type": "object", "properties": {}}}},
]

SYSTEM_PROMPT = (
    "You are a coding agent working in a sandbox directory. Use the provided "
    "tools to read, edit, and run code. When the task is complete, call the "
    "`done` tool. Do not explain — act. You have a maximum of "
    f"{MAX_TURNS} tool-call turns."
)


def _dispatch(tool_name: str, args: Dict[str, Any], work_dir: Path) -> str:
    try:
        if tool_name == "read_file":
            p = (work_dir / args["path"]).resolve()
            if not str(p).startswith(str(work_dir.resolve())):
                return "error: path outside sandbox"
            return p.read_text(errors="replace")[:4000]
        if tool_name == "write_file":
            p = (work_dir / args["path"]).resolve()
            if not str(p).startswith(str(work_dir.resolve())):
                return "error: path outside sandbox"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"])
            return f"wrote {len(args['content'])} bytes to {args['path']}"
        if tool_name == "list_dir":
            p = (work_dir / args.get("path", ".")).resolve()
            if not str(p).startswith(str(work_dir.resolve())):
                return "error: path outside sandbox"
            return "\n".join(sorted(e.name for e in p.iterdir()))[:2000]
        if tool_name == "run_bash":
            r = subprocess.run(
                ["bash", "-c", args["command"]],
                cwd=work_dir, capture_output=True, text=True, timeout=60
            )
            return (r.stdout + r.stderr)[:4000]
        if tool_name == "done":
            return "done"
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"
    return f"unknown tool: {tool_name}"


def run(task_prompt: str, work_dir: Path, model_client: Any, timeout_sec: int) -> AgentRunResult:
    """model_client is an OpenAI-compatible client with .chat(messages, tools=...).

    Returns when `done` is called, turn limit reached, or timeout exceeded.
    """
    start = time.time()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_prompt},
    ]
    last_tool = None
    for turn in range(MAX_TURNS):
        if time.time() - start > timeout_sec:
            return AgentRunResult(
                status="timeout", elapsed_sec=time.time() - start,
                turns_completed=turn, last_tool_call=last_tool,
            )
        try:
            content, tool_calls, _, _ = model_client.chat(messages, tools=TOOLS)
        except Exception as e:
            return AgentRunResult(
                status="error", elapsed_sec=time.time() - start,
                turns_completed=turn, error=f"{type(e).__name__}: {e}",
            )
        if not tool_calls:
            # Model answered without a tool — treat as implicit done.
            return AgentRunResult(
                status="scored", elapsed_sec=time.time() - start,
                turns_completed=turn, last_tool_call=last_tool,
                stdout_excerpt=(content or "")[:500],
            )
        # Append assistant turn.
        messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", "")
            raw_args = tc.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            last_tool = f"{name}({','.join(args.keys())})"
            if name == "done":
                return AgentRunResult(
                    status="scored", elapsed_sec=time.time() - start,
                    turns_completed=turn + 1, last_tool_call=last_tool,
                )
            output = _dispatch(name, args, work_dir)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", "call_" + str(turn)),
                "content": output,
            })
    return AgentRunResult(
        status="scored", elapsed_sec=time.time() - start,
        turns_completed=MAX_TURNS, last_tool_call=last_tool,
        stdout_excerpt="max turns reached",
    )
