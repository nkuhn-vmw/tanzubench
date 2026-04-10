#!/usr/bin/env python3
"""Pretty-print a v2 benchmark result JSON file.

Usage:
    python3 tools/format-results.py <file.json>
    python3 tools/format-results.py -          # read from stdin
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def format_one(d: dict, label: str = "") -> None:
    meta = d.get("meta", {})
    target = d.get("target", {})
    summary = d.get("summary", {})
    tests = d.get("tests", [])

    print("=" * 60)
    if label:
        print(f"  File: {label}")
    model = target.get("display_name") or target.get("name", "?")
    tag = meta.get("tag", "")
    tag_str = f" [{tag}]" if tag else ""
    print(f"  Model: {model}{tag_str}")
    print(f"  Date:  {meta.get('timestamp', '?')}")
    print(f"  Foundation: {meta.get('foundation', '?')}")

    composite = summary.get("composite_score")
    if composite is not None:
        print(f"  Composite score: {composite:.1f}")

    cat_scores = summary.get("category_scores", [])
    if cat_scores:
        print("  Category scores:")
        for entry in sorted(cat_scores, key=lambda e: e.get("category", "")):
            cat = entry.get("category", "?")
            score = entry.get("score")
            score_str = f"{score:.1f}" if score is not None else "—"
            print(f"    {cat:<20} {score_str}")

    print(f"  Tests: {len(tests)}")
    print()

    if tests:
        # Group by category
        by_cat: dict[str, list[dict]] = {}
        for t in tests:
            cat = t.get("category", "uncategorized")
            by_cat.setdefault(cat, []).append(t)

        for cat, cat_tests in sorted(by_cat.items()):
            print(f"  [{cat}]")
            print(f"  {'Test':<30} {'Status':<8} {'Score':>6} {'Latency':>9}")
            print(f"  {'-'*30} {'-'*8} {'-'*6} {'-'*9}")
            for t in cat_tests:
                name = t.get("id") or t.get("name", "?")
                status = t.get("status", "?")
                score = t.get("score")
                score_str = f"{score:.2f}" if score is not None else "—"
                elapsed = t.get("elapsed_ms", 0)
                lat_str = f"{elapsed/1000:.1f}s" if elapsed else "—"
                print(f"  {name:<30} {status:<8} {score_str:>6} {lat_str:>9}")
            print()

    print("=" * 60)
    print()


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("Usage: format-results.py <file.json> [...]  or  - for stdin", file=sys.stderr)
        return 1

    for arg in args:
        if arg == "-":
            try:
                d = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                print(f"ERROR: invalid JSON from stdin: {e}", file=sys.stderr)
                return 1
            format_one(d)
        else:
            p = Path(arg)
            try:
                d = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError) as e:
                print(f"ERROR: {arg}: {e}", file=sys.stderr)
                return 1
            format_one(d, arg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
