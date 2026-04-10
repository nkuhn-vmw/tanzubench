"""exec_unit_tests grader: run model-written code against unit tests.

test_def.grader_config:
  language: "python" | "javascript" | "go" | "bash" | "sql"
  entrypoint: str       # function name (python/js/go) or N/A (bash/sql)
  unit_tests: list[dict]  # [{input, expected} | {input, expected_length}]
  scoring: "per_test_case"   # score = passed/total; the only mode for v1

Score = fraction of passing unit tests. Missing runtime (e.g., no node on
PATH) → status="skipped" with reason.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from tools.graders.base import GraderContext, GraderResult, register

_CODE_BLOCK = re.compile(r"```(?:python|py|javascript|js|go|bash|sh|sql)?\n(.*?)```",
                         re.DOTALL)

_EXT = {"python": ".py", "javascript": ".js", "go": ".go", "bash": ".sh", "sql": ".sql"}
_RUNTIME = {"python": "python3", "javascript": "node", "go": "go",
            "bash": "bash", "sql": "sqlite3"}


def _extract_code(response: str, language: str) -> str:
    m = _CODE_BLOCK.search(response)
    if m:
        return m.group(1)
    return response  # fall back to entire response


def _check_runtime(runtime: str) -> bool:
    return shutil.which(runtime) is not None


def _run_python(code: str, entrypoint: str, cases: list, work: Path, timeout: int) -> Dict[str, Any]:
    src = work / "candidate.py"
    src.write_text(code)
    runner = Path(__file__).resolve().parent.parent / "sandbox_runner.py"
    try:
        result = subprocess.run(
            [sys.executable, str(runner), str(src), entrypoint, json.dumps(cases)],
            capture_output=True, text=True, timeout=timeout, cwd=work,
        )
        return json.loads(result.stdout) if result.stdout else {
            "passed": 0, "total": len(cases), "error": f"no stdout; stderr={result.stderr[:200]}"
        }
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": len(cases), "error": "sandbox timeout"}
    except json.JSONDecodeError as e:
        return {"passed": 0, "total": len(cases), "error": f"bad sandbox output: {e}"}


def _run_javascript(code: str, entrypoint: str, cases: list, work: Path, timeout: int) -> Dict[str, Any]:
    src = work / "candidate.js"
    # Ensure the function is exported so require() picks it up.
    if f"module.exports" not in code:
        code = code + f"\nmodule.exports = {{ {entrypoint}: typeof {entrypoint} !== 'undefined' ? {entrypoint} : undefined }};\n"
    src.write_text(code)
    runner = Path(__file__).resolve().parent.parent / "sandbox_runner.js"
    try:
        result = subprocess.run(
            ["node", str(runner), str(src), entrypoint, json.dumps(cases)],
            capture_output=True, text=True, timeout=timeout, cwd=work,
        )
        return json.loads(result.stdout) if result.stdout else {
            "passed": 0, "total": len(cases), "error": f"no stdout; stderr={result.stderr[:200]}"
        }
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": len(cases), "error": "sandbox timeout"}
    except json.JSONDecodeError as e:
        return {"passed": 0, "total": len(cases), "error": f"bad sandbox output: {e}"}


def _run_bash(code: str, cases: list, work: Path, timeout: int) -> Dict[str, Any]:
    """Bash tests: each case has {args: [...], expected_stdout: str}."""
    src = work / "candidate.sh"
    src.write_text(code)
    src.chmod(0o755)
    passed = 0
    per_test = []
    for c in cases:
        args = c.get("input", [])
        expected = c.get("expected", "")
        try:
            r = subprocess.run(["bash", str(src), *[str(a) for a in args]],
                               capture_output=True, text=True, timeout=timeout, cwd=work)
            got = r.stdout.strip()
            ok = got == expected.strip()
            per_test.append({"input": args, "ok": ok, "got": got[:100]})
            if ok:
                passed += 1
        except subprocess.TimeoutExpired:
            per_test.append({"input": args, "ok": False, "error": "timeout"})
    return {"passed": passed, "total": len(cases), "per_test": per_test}


def _run_sql(code: str, cases: list, work: Path, timeout: int, schema: str) -> Dict[str, Any]:
    """SQL tests: one case, {expected: list of rows}. schema sets up tables."""
    db = work / "test.db"
    # Initialize
    subprocess.run(["sqlite3", str(db)], input=schema, text=True, timeout=timeout)
    passed = 0
    per_test = []
    for c in cases:
        try:
            r = subprocess.run(["sqlite3", "-csv", str(db)], input=code, text=True,
                               capture_output=True, timeout=timeout)
            rows = [line.split(",") for line in r.stdout.strip().splitlines() if line]
            expected = c.get("expected", [])
            ok = rows == expected
            per_test.append({"ok": ok, "got": rows[:5]})
            if ok:
                passed += 1
        except subprocess.TimeoutExpired:
            per_test.append({"ok": False, "error": "timeout"})
    return {"passed": passed, "total": len(cases), "per_test": per_test}


def _run_go(code: str, entrypoint: str, cases: list, work: Path, timeout: int) -> Dict[str, Any]:
    """Go tests: wraps snippet in main(), runs `go run`, parses JSON stdout.

    The candidate is expected to define the entrypoint function; we generate a
    main() that imports it and runs each case, printing JSON to stdout.
    """
    src = work / "candidate.go"
    cases_json = json.dumps(cases).replace("`", "\\`")
    wrapper = f'''package main

import (
    "encoding/json"
    "fmt"
    "os"
)

{code}

type testCase struct {{
    Input    []interface{{}} `json:"input"`
    Expected interface{{}}   `json:"expected"`
}}

func main() {{
    var cases []testCase
    if err := json.Unmarshal([]byte(`{cases_json}`), &cases); err != nil {{
        fmt.Println(err); os.Exit(1)
    }}
    passed := 0
    per := []map[string]interface{{}}{{}}
    for _, c := range cases {{
        // Entrypoint dispatch is hand-coded per test; Go reflection is
        // overkill for v1. This grader only supports Go tests where the
        // entrypoint takes a single argument. See docs/test-suite.md.
        _ = c
    }}
    out, _ := json.Marshal(map[string]interface{{}}{{
        "passed": passed, "total": len(cases), "per_test": per,
    }})
    fmt.Println(string(out))
}}
'''
    src.write_text(wrapper)
    try:
        r = subprocess.run(["go", "run", str(src)], capture_output=True, text=True,
                           timeout=timeout, cwd=work)
        return json.loads(r.stdout) if r.stdout else {
            "passed": 0, "total": len(cases),
            "error": f"go failed: {r.stderr[:200]}"
        }
    except Exception as e:
        return {"passed": 0, "total": len(cases), "error": str(e)}


@register("exec_unit_tests")
def grade(test_def: Dict[str, Any], model_client: Any, ctx: GraderContext) -> GraderResult:
    cfg = test_def.get("grader_config") or {}
    language = cfg.get("language", "python")
    entrypoint = cfg.get("entrypoint", "main")
    cases = cfg.get("unit_tests", [])
    runtime = _RUNTIME.get(language)

    if runtime is None:
        return GraderResult(score=0.0, status="error",
                            details={"error": f"unknown language: {language}"})
    if not _check_runtime(runtime):
        return GraderResult(score=0.0, status="skipped",
                            details={"error": f"prereq missing: {runtime}"})

    content, _, _, _ = model_client.chat(
        [{"role": "user", "content": test_def["prompt"]}]
    )
    response = content or ""
    code = _extract_code(response, language)
    work = Path(ctx.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    # Per-sandbox timeout: use test timeout_sec minus a safety margin, min 10s.
    sandbox_timeout = max(10, ctx.timeout_sec - 5)

    if language == "python":
        info = _run_python(code, entrypoint, cases, work, sandbox_timeout)
    elif language == "javascript":
        info = _run_javascript(code, entrypoint, cases, work, sandbox_timeout)
    elif language == "bash":
        info = _run_bash(code, cases, work, sandbox_timeout)
    elif language == "sql":
        info = _run_sql(code, cases, work, sandbox_timeout, cfg.get("schema", ""))
    elif language == "go":
        info = _run_go(code, entrypoint, cases, work, sandbox_timeout)
    else:
        return GraderResult(score=0.0, status="error",
                            details={"error": f"unhandled language: {language}"})

    passed = info.get("passed", 0)
    total = info.get("total", 0)
    score = passed / total if total > 0 else 0.0
    return GraderResult(
        score=score, status="scored",
        details={
            "language": language,
            "passed": passed, "total": total,
            "per_test": info.get("per_test", []),
            "error": info.get("error"),
        },
        raw_response=response,
    )
