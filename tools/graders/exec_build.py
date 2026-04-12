"""Stub — implemented in PR 3."""
from tools.graders.base import GraderResult, register

@register("exec_build")
def grade(test_def, model_client, ctx):
    return GraderResult(score=0.0, status="error", details={"error": "not implemented"})
