"""Stub — implemented in PR 5."""
from tools.graders.base import GraderResult, register

@register("container_exec")
def grade(test_def, model_client, ctx):
    return GraderResult(score=0.0, status="error", details={"error": "not implemented"})
