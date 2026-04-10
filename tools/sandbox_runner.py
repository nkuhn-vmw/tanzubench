#!/usr/bin/env python3
"""Sandboxed Python execution helper for the exec_unit_tests grader.

Usage: python3 sandbox_runner.py <candidate_file> <entrypoint> <test_cases_json>

Imports the candidate file as a module, calls the entrypoint function with
each test case's input, compares against expected output, prints JSON to
stdout: {"passed": int, "total": int, "per_test": [{"input": ..., "ok": bool, "error": str|None}]}

Exit 0 always (errors are reported in the JSON payload). The caller wraps
us in `timeout` and `ulimit` at the shell level.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _match(got, expected, expected_length):
    if expected_length is not None:
        try:
            return len(got) == expected_length
        except TypeError:
            return False
    return got == expected


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"passed": 0, "total": 0,
                          "error": "usage: sandbox_runner.py <file> <fn> <cases_json>"}))
        return 0
    path = Path(sys.argv[1])
    entrypoint = sys.argv[2]
    cases = json.loads(sys.argv[3])

    try:
        mod = load_module(path)
    except Exception as e:
        print(json.dumps({"passed": 0, "total": len(cases),
                          "error": f"import failed: {e}",
                          "traceback": traceback.format_exc()[:500]}))
        return 0

    fn = getattr(mod, entrypoint, None)
    if fn is None:
        print(json.dumps({"passed": 0, "total": len(cases),
                          "error": f"entrypoint {entrypoint!r} not found"}))
        return 0

    per_test = []
    passed = 0
    for case in cases:
        inp = case.get("input", [])
        expected = case.get("expected")
        expected_length = case.get("expected_length")
        try:
            got = fn(*inp)
            ok = _match(got, expected, expected_length)
            per_test.append({"input": inp, "ok": ok,
                             "got": repr(got)[:100]})
            if ok:
                passed += 1
        except Exception as e:
            per_test.append({"input": inp, "ok": False,
                             "error": f"{type(e).__name__}: {e}"[:200]})

    print(json.dumps({"passed": passed, "total": len(cases), "per_test": per_test}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
