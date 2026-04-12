"""Grader plugin package. Graders are registered via @register in base.py."""
from tools.graders.base import GraderContext, GraderResult, get_grader, register

# Importing each grader module triggers its @register decorator call.
# Imports are at the bottom to avoid circular imports with base.
from tools.graders import (  # noqa: E402,F401
    exact_match,
    contains,
    regex,
    tool_call,
    needle,
    file_check,
    exec_unit_tests,
    llm_judge,
    json_schema,
    multi_turn,
    exec_build,
    container_exec,
    agentic,
)

__all__ = ["GraderContext", "GraderResult", "get_grader", "register"]
