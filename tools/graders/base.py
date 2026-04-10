"""Grader plugin base: GraderResult, GraderContext, and the plugin registry.

Each grader module defines a `grade(test_def, model_client, ctx)` function
and registers itself with `@register("<name>")`. The runner calls
`get_grader(name)` to dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class GraderResult:
    """Return value from every grader.

    score: 0.0 to 1.0, normalized.
    status: one of "scored", "skipped", "timeout", "error".
    details: free-form per-grader payload (documented in each grader module).
    raw_response: the model's raw text response, for auditability. None for
                  agentic grader (which doesn't have a single response).
    """
    score: float
    status: str
    details: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[str] = None


@dataclass
class GraderContext:
    """Runtime context passed to every grader by the runner.

    model_client: OpenAI-compatible client for the target model. Has .chat()
                  returning (content, tool_calls, completion_tokens, elapsed_s).
    judge_client: OpenAI-compatible client for the judge model. None if no
                  judge is configured — llm_judge grader must skip cleanly.
    work_dir: Path for any scratch files. Cleaned between tests.
    assets_dir: Path to tests/assets/ for asset: substitutions.
    fixtures_dir: Path to tests/agentic/fixtures/ for agentic grader.
    timeout_sec: The per-test wall-clock budget the runner will enforce.
    """
    model_client: Any
    judge_client: Optional[Any]
    work_dir: Any  # pathlib.Path
    assets_dir: Any
    fixtures_dir: Any
    timeout_sec: int


GraderFn = Callable[[Dict[str, Any], Any, GraderContext], GraderResult]

_REGISTRY: Dict[str, GraderFn] = {}


def register(name: str) -> Callable[[GraderFn], GraderFn]:
    """Decorator used by each grader module to register itself."""
    def _wrap(fn: GraderFn) -> GraderFn:
        if name in _REGISTRY:
            raise RuntimeError(f"grader {name!r} already registered")
        _REGISTRY[name] = fn
        return fn
    return _wrap


def get_grader(name: str) -> GraderFn:
    """Look up a grader by name. Raises KeyError if not registered."""
    if name not in _REGISTRY:
        raise KeyError(f"no grader registered for {name!r}. "
                       f"Known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]
