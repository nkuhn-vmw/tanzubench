"""Pytest suite for graders. Grows across Tasks 3-7."""
from __future__ import annotations

import pytest

from tools.graders.base import GraderResult, get_grader, register


def test_registry_rejects_duplicate():
    @register("__test_dup__")
    def _fn(test_def, client, ctx):
        return GraderResult(score=1.0, status="scored")

    with pytest.raises(RuntimeError, match="already registered"):
        @register("__test_dup__")
        def _fn2(test_def, client, ctx):
            return GraderResult(score=0.0, status="scored")


def test_registry_raises_on_unknown():
    with pytest.raises(KeyError, match="no grader registered"):
        get_grader("does-not-exist")


from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple


@dataclass
class FakeClient:
    """Test double for model_client. Replays canned responses in order."""
    responses: List[Tuple[str, list, int, float]] = field(default_factory=list)
    calls: List[dict] = field(default_factory=list)

    def chat(self, messages, tools=None):
        self.calls.append({"messages": messages, "tools": tools})
        if not self.responses:
            return ("", [], 0, 0.0)
        return self.responses.pop(0)


def _ctx(tmp_path: Path) -> "GraderContext":
    from tools.graders.base import GraderContext
    return GraderContext(
        model_client=None,
        judge_client=None,
        work_dir=tmp_path / "work",
        assets_dir=tmp_path / "assets",
        fixtures_dir=tmp_path / "fixtures",
        timeout_sec=60,
    )


def test_exact_match_pass():
    from tools.graders.exact_match import grade
    client = FakeClient(responses=[("Paris", [], 5, 0.1)])
    result = grade(
        {"prompt": "Capital of France?", "grader_config": {"expected_answer": "Paris"}},
        client, _ctx(Path("/tmp")),
    )
    assert result.score == 1.0
    assert result.status == "scored"
    assert result.details["matched"] is True


def test_exact_match_fail():
    from tools.graders.exact_match import grade
    client = FakeClient(responses=[("London", [], 5, 0.1)])
    result = grade(
        {"prompt": "?", "grader_config": {"expected_answer": "Paris"}},
        client, _ctx(Path("/tmp")),
    )
    assert result.score == 0.0


def test_contains_pass_and_fail():
    from tools.graders.contains import grade
    ctx = _ctx(Path("/tmp"))
    ok = FakeClient(responses=[("The answer is 42, definitely.", [], 5, 0.1)])
    r = grade({"prompt": "?", "grader_config": {"must_contain": ["42"],
                                                "must_not_contain": ["maybe"]}},
              ok, ctx)
    assert r.score == 1.0
    bad = FakeClient(responses=[("maybe 42", [], 5, 0.1)])
    r2 = grade({"prompt": "?", "grader_config": {"must_contain": ["42"],
                                                 "must_not_contain": ["maybe"]}},
               bad, ctx)
    assert r2.score == 0.0
    assert r2.details["forbidden"] == ["maybe"]


def test_regex_pass_and_must_not():
    from tools.graders.regex import grade
    ctx = _ctx(Path("/tmp"))
    ok = FakeClient(responses=[("version 1.2.3", [], 5, 0.1)])
    r = grade({"prompt": "?", "grader_config": {"pattern": r"\d+\.\d+\.\d+"}},
              ok, ctx)
    assert r.score == 1.0
    bad = FakeClient(responses=[("version 1.2.3 DRAFT", [], 5, 0.1)])
    r2 = grade({"prompt": "?", "grader_config": {
        "pattern": r"\d+\.\d+\.\d+",
        "must_not_match": ["DRAFT"]
    }}, bad, ctx)
    assert r2.score == 0.0


def test_tool_call_single_pass():
    from tools.graders.tool_call import grade
    tc = [{"function": {"name": "get_weather",
                        "arguments": '{"location": "Paris"}'}}]
    client = FakeClient(responses=[("", tc, 5, 0.1)])
    r = grade({"prompt": "weather in paris?", "grader_config": {
        "tools": [], "mode": "single",
        "expected_tool": "get_weather",
        "expected_param_key": "location",
        "expected_param_contains": "Paris"
    }}, client, _ctx(Path("/tmp")))
    assert r.score == 1.0


def test_tool_call_restraint():
    from tools.graders.tool_call import grade
    client = FakeClient(responses=[("4", [], 5, 0.1)])
    r = grade({"prompt": "2+2?", "grader_config": {
        "tools": [], "mode": "restraint", "expected_answer": "4"
    }}, client, _ctx(Path("/tmp")))
    assert r.score == 1.0


def test_needle_normalize_unicode_and_markdown():
    from tools.graders.needle import _normalize
    # gpt-oss-120b emits non-breaking hyphens + markdown bold around needles
    assert _normalize("ALPHA-SEVEN-NINE-TWO") == _normalize("**ALPHA\u2011SEVEN\u2011NINE\u2011TWO**")
    assert _normalize("bravo-eight") == _normalize("BRAVO\u2013EIGHT")  # en-dash
    assert _normalize("charlie-two-one") == _normalize("charlie\u2014two\u2014one")  # em-dash


def test_needle_grader(tmp_path):
    from tools.graders.needle import grade
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "haystack.txt").write_text("filler " * 1000)
    ctx_obj = _ctx(tmp_path)
    client = FakeClient(responses=[("The magic code is ALPHA-99.", [], 20, 0.2)])
    r = grade({"prompt_template": "", "grader_config": {
        "haystack_asset": "haystack.txt",
        "needle": "The magic code is ALPHA-99.",
        "depth": 0.5,
        "question": "What is the magic code?",
        "expected_answer": "ALPHA-99",
    }}, client, ctx_obj)
    assert r.score == 1.0
    assert r.details["matched"] is True


def test_file_check_writes_and_checks(tmp_path):
    from tools.graders.file_check import grade
    ctx_obj = _ctx(tmp_path)
    client = FakeClient(responses=[("hello world", [], 5, 0.1)])
    r = grade({"prompt": "write hello world", "grader_config": {
        "write_response_to": "out.txt",
        "file_checks": [
            {"path": "out.txt", "must_exist": True, "must_contain": ["hello"]}
        ]
    }}, client, ctx_obj)
    assert r.score == 1.0
    assert (tmp_path / "work" / "out.txt").read_text() == "hello world"


def test_exec_python_fizzbuzz(tmp_path):
    from tools.graders.exec_unit_tests import grade
    ctx_obj = _ctx(tmp_path)
    code = """```python
def fizzbuzz(n):
    out = []
    for i in range(1, n+1):
        if i % 15 == 0: out.append("FizzBuzz")
        elif i % 3 == 0: out.append("Fizz")
        elif i % 5 == 0: out.append("Buzz")
        else: out.append(str(i))
    return out
```"""
    client = FakeClient(responses=[(code, [], 100, 1.0)])
    r = grade({"prompt": "write fizzbuzz", "grader_config": {
        "language": "python",
        "entrypoint": "fizzbuzz",
        "unit_tests": [
            {"input": [5], "expected": ["1","2","Fizz","4","Buzz"]},
            {"input": [15], "expected_length": 15},
            {"input": [0], "expected": []},
        ]
    }}, client, ctx_obj)
    assert r.score == 1.0
    assert r.details["passed"] == 3


def test_exec_python_broken_code_scores_zero(tmp_path):
    from tools.graders.exec_unit_tests import grade
    ctx_obj = _ctx(tmp_path)
    client = FakeClient(responses=[("```python\ndef fizzbuzz(n): return 'nope'\n```", [], 10, 0.1)])
    r = grade({"prompt": "?", "grader_config": {
        "language": "python", "entrypoint": "fizzbuzz",
        "unit_tests": [{"input": [3], "expected": ["1","2","Fizz"]}]
    }}, client, ctx_obj)
    assert r.score == 0.0


def test_llm_judge_skipped_when_no_judge(tmp_path):
    from tools.graders.llm_judge import grade
    ctx_obj = _ctx(tmp_path)  # judge_client is None
    ctx_obj.judge_client = None
    client = FakeClient(responses=[("whatever", [], 10, 0.1)])
    r = grade({"prompt": "?", "grader_config": {"judge_rubric": "grade"}},
              client, ctx_obj)
    assert r.status == "skipped"
    assert r.score == 0.0


def test_llm_judge_parses_rubric(tmp_path):
    from tools.graders.llm_judge import grade
    ctx_obj = _ctx(tmp_path)
    target = FakeClient(responses=[("A clear summary here.", [], 30, 0.5)])
    judge_raw = '{"clarity": 0.9, "accuracy": 0.8, "follows_constraints": 1.0, "rationale": "good"}'
    judge = FakeClient(responses=[(judge_raw, [], 20, 0.3)])
    # Monkey-patch chat to accept kwargs
    orig_chat = judge.chat
    judge.chat = lambda messages, temperature=0.0, response_format=None: orig_chat(messages)
    ctx_obj.judge_client = judge
    r = grade({"prompt": "summarize", "grader_config": {
        "judge_rubric": "grade on clarity, accuracy, follows_constraints",
        "judge_aggregation": "mean",
    }}, target, ctx_obj)
    assert r.status == "scored"
    assert abs(r.score - 0.9) < 0.01  # mean of 0.9, 0.8, 1.0 = 0.9


def test_llm_judge_retries_then_fails(tmp_path):
    from tools.graders.llm_judge import grade
    ctx_obj = _ctx(tmp_path)
    target = FakeClient(responses=[("response", [], 10, 0.1)])
    junk = FakeClient(responses=[
        ("not json at all", [], 10, 0.1),
        ("still bad", [], 10, 0.1),
        ("nope", [], 10, 0.1),
    ])
    orig = junk.chat
    junk.chat = lambda messages, temperature=0.0, response_format=None: orig(messages)
    ctx_obj.judge_client = junk
    r = grade({"prompt": "?", "grader_config": {
        "judge_rubric": "grade it",
        "judge_max_retries": 2,
    }}, target, ctx_obj)
    assert r.status == "error"
    assert r.details["judge"]["judge_parse_failure"] is True


def test_agentic_grade_single_entry_errors(tmp_path):
    from tools.graders.agentic import grade
    ctx_obj = _ctx(tmp_path)
    r = grade({"id": "x", "fixture": "none", "task_prompt": "do thing"},
              None, ctx_obj)
    assert r.status == "error"
    assert "grade_multi" in r.details["error"]


def test_json_schema_valid():
    from tools.graders.json_schema import grade
    client = FakeClient(responses=[('{"name": "alice", "age": 30}', [], 10, 0.1)])
    r = grade({"prompt": "?", "grader_config": {
        "schema": {"type": "object", "required": ["name", "age"],
                   "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}},
        "expected_values": {"name": "alice", "age": "30"},
    }}, client, _ctx(Path("/tmp")))
    assert r.score > 0.9
    assert r.details["parse_ok"] is True
    assert r.details["schema_score"] == 1.0


def test_json_schema_invalid_type():
    from tools.graders.json_schema import grade
    client = FakeClient(responses=[('{"name": "alice", "age": "thirty"}', [], 10, 0.1)])
    r = grade({"prompt": "?", "grader_config": {
        "schema": {"type": "object", "required": ["name", "age"],
                   "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}},
    }}, client, _ctx(Path("/tmp")))
    assert r.details["parse_ok"] is True
    assert r.details["schema_score"] < 1.0
    assert 0 < r.score < 1.0  # partial credit


def test_json_schema_no_json():
    from tools.graders.json_schema import grade
    client = FakeClient(responses=[("I don't know how to make JSON.", [], 10, 0.1)])
    r = grade({"prompt": "?", "grader_config": {
        "schema": {"type": "object"},
    }}, client, _ctx(Path("/tmp")))
    assert r.score == 0.0
    assert r.details["parse_ok"] is False


def test_json_schema_markdown_fenced():
    from tools.graders.json_schema import grade
    client = FakeClient(responses=[('Here is the JSON:\n```json\n{"x": 1}\n```\nDone.', [], 10, 0.1)])
    r = grade({"prompt": "?", "grader_config": {
        "schema": {"type": "object", "required": ["x"],
                   "properties": {"x": {"type": "integer"}}},
    }}, client, _ctx(Path("/tmp")))
    assert r.details["parse_ok"] is True
    assert r.score > 0.9


def test_multi_turn_basic():
    from tools.graders.multi_turn import grade
    # Simulate a 2-turn conversation where model always responds "Hello Sarah, here is your update."
    responses = [
        ("Hello Sarah, here is your update about the delay.", [], 30, 0.2),
        ("Sorry Sarah, the new deadline is April 25.", [], 25, 0.2),
    ]
    client = FakeClient(responses=responses)
    r = grade({"prompt": "", "grader_config": {
        "turns": [
            {"user_message": "Write an email to Sarah about a delay.",
             "checks": [{"contains": "Sarah"}, {"contains": "delay"}]},
            {"user_message": "Add a deadline of April 25.",
             "checks": [{"contains": "April 25"}, {"any_contains": ["sorry", "apologize"]}]},
        ]
    }}, client, _ctx(Path("/tmp")))
    assert r.score == 1.0
    assert r.details["total_passed"] == 4
    assert r.details["total_checks"] == 4


def test_exec_build_pass(tmp_path):
    from tools.graders.exec_build import grade
    client = FakeClient(responses=[('{"name": "test", "version": "1.0.0"}', [], 10, 0.1)])
    ctx_obj = _ctx(tmp_path)
    r = grade({"prompt": "fix this", "grader_config": {
        "target_file": "data.json",
        "build_command": "python3 -c \"import json; json.load(open('data.json'))\"",
        "build_tool": "python3",
    }}, client, ctx_obj)
    assert r.score == 1.0
    assert r.details["build_ok"] is True


def test_exec_build_fail(tmp_path):
    from tools.graders.exec_build import grade
    client = FakeClient(responses=[("not valid json at all", [], 10, 0.1)])
    ctx_obj = _ctx(tmp_path)
    r = grade({"prompt": "fix this", "grader_config": {
        "target_file": "data.json",
        "build_command": "python3 -c \"import json; json.load(open('data.json'))\"",
        "build_tool": "python3",
    }}, client, ctx_obj)
    assert r.score == 0.0
    assert r.details["build_ok"] is False


def test_multi_turn_partial():
    from tools.graders.multi_turn import grade
    client = FakeClient(responses=[
        ("Here is a short note.", [], 10, 0.1),
    ])
    r = grade({"prompt": "", "grader_config": {
        "turns": [
            {"user_message": "Write something with Sarah.",
             "checks": [{"contains": "Sarah"}, {"length_max": 20}]},
        ]
    }}, client, _ctx(Path("/tmp")))
    # "Sarah" not in response, but length check passes
    assert r.score == 0.5
    assert r.details["total_passed"] == 1


def test_multi_turn_tool_result_injection():
    from tools.graders.multi_turn import grade
    client = FakeClient(responses=[
        ("", [{"function": {"name": "get_weather", "arguments": '{"location":"Paris"}'}}], 5, 0.1),
        ("Yes, bring an umbrella since it's rainy.", [], 15, 0.1),
    ])
    r = grade({"prompt": "", "grader_config": {
        "turns": [
            {"user_message": "What's the weather in Paris?",
             "tools": [{"type": "function", "function": {"name": "get_weather", "parameters": {}}}],
             "checks": [{"tool_called": "get_weather"}]},
            {"user_message": "Should I bring an umbrella?",
             "tool_result": {"tool_call_id": "call_0", "content": "18°C, rainy"},
             "checks": [{"any_contains": ["umbrella", "rain"]}]},
        ]
    }}, client, _ctx(Path("/tmp")))
    assert r.score == 1.0


def test_container_exec_falls_back_to_local_without_docker(tmp_path, monkeypatch):
    from tools.graders.container_exec import grade
    monkeypatch.setattr("shutil.which", lambda x: None if x == "docker" else "/usr/bin/" + x)
    client = FakeClient(responses=[("echo hello", [], 5, 0.1)])
    ctx_obj = _ctx(tmp_path)
    r = grade({"prompt": "do something", "grader_config": {"image": "ubuntu:22.04", "state_checks": []}},
              client, ctx_obj)
    assert r.status == "scored"
    assert r.details.get("mode") == "local"
