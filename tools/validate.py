#!/usr/bin/env python3
"""Validate benchmark result files or test definitions.

Usage:
    python3 tools/validate.py <path>               # validates results
    python3 tools/validate.py --tests <path>       # validates test YAMLs

Exits non-zero if any file fails validation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("ERROR: jsonschema package is required. pip install jsonschema", file=sys.stderr)
    sys.exit(2)

try:
    import yaml
except ImportError:
    yaml = None

REPO = Path(__file__).resolve().parent.parent
RESULT_SCHEMA_PATH = REPO / "schema" / "result-v2.schema.json"
TEST_SCHEMA_PATH = REPO / "schema" / "test-v1.schema.json"


def iter_files(path: Path, exts: tuple[str, ...]) -> Iterator[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        for ext in exts:
            yield from sorted(path.rglob(f"*{ext}"))
    else:
        raise FileNotFoundError(f"not a file or directory: {path}")


def validate_result_file(path: Path, v: Draft202012Validator) -> list[str]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"{path}: invalid JSON - {e}"]
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    return [f"{path}: {'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in errs]


def validate_test_file(path: Path, v: Draft202012Validator) -> list[str]:
    if yaml is None:
        return [f"{path}: pyyaml required for --tests"]
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        return [f"{path}: YAML error - {e}"]
    if not isinstance(data, dict):
        return [f"{path}: not a dict"]
    errs = sorted(v.iter_errors(data), key=lambda e: list(e.path))
    msgs = [f"{path}: {'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in errs]
    if data.get("id") != path.stem:
        msgs.append(f"{path}: id {data.get('id')!r} does not match filename")
    return msgs


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tests", action="store_true",
                   help="validate test YAML definitions instead of results")
    p.add_argument("path", help="file or directory")
    args = p.parse_args()

    target = Path(args.path)
    if args.tests:
        schema_path = TEST_SCHEMA_PATH
        files = [f for f in iter_files(target, (".yaml", ".yml"))
                 if "fixtures" not in f.parts and "assets" not in f.parts]
        validate = validate_test_file
    else:
        schema_path = RESULT_SCHEMA_PATH
        files = list(iter_files(target, (".json",)))
        validate = validate_result_file

    try:
        schema = json.loads(schema_path.read_text())
    except Exception as e:
        print(f"ERROR: cannot load schema {schema_path}: {e}", file=sys.stderr)
        return 2
    validator = Draft202012Validator(schema)

    if not files:
        print(f"OK: no files under {target}")
        return 0

    all_errs = []
    for f in files:
        errs = validate(f, validator)
        if errs:
            all_errs.extend(errs)

    if all_errs:
        for m in all_errs:
            print(m, file=sys.stderr)
        print(f"FAIL: {len(all_errs)} error(s) across {len(files)} file(s)", file=sys.stderr)
        return 1
    print(f"OK: {len(files)} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
