#!/usr/bin/env python3
"""Compare two or more v2 benchmark result files side-by-side.

Usage:
    python3 tools/compare-results.py a.json b.json [c.json ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def label(d: dict) -> str:
    meta = d.get("meta", {})
    target = d.get("target", {})
    tag = meta.get("tag", "")
    name = target.get("display_name") or target.get("name", "?")
    return f"{name}[{tag}]" if tag else name


def main() -> int:
    paths = sys.argv[1:]
    if len(paths) < 2:
        print("Usage: compare-results.py <a.json> <b.json> [c.json ...]", file=sys.stderr)
        return 1

    results = []
    for p in paths:
        try:
            results.append((p, load(p)))
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR: {p}: {e}", file=sys.stderr)
            return 1

    labels = [label(d) for _, d in results]
    col_w = max(20, *(len(l) for l in labels)) + 2

    print("=" * 72)
    print("  Comparing:")
    for path, d in results:
        meta = d.get("meta", {})
        lbl = label(d)
        print(f"    {lbl} | {meta.get('foundation','?')} | {meta.get('timestamp','?')}")
    print("=" * 72)
    print()

    # Composite scores
    print(f"  {'Composite score':<25}", end="")
    for _, d in results:
        score = d.get("summary", {}).get("composite_score")
        s = f"{score:.1f}" if score is not None else "—"
        print(f"  {s:>{col_w}}", end="")
    print()
    print()

    # Category scores — category_scores is a list of {category, score, ...}
    def cat_score_map(d: dict) -> dict[str, float | None]:
        return {e["category"]: e.get("score")
                for e in d.get("summary", {}).get("category_scores", [])}

    all_cats: set[str] = set()
    for _, d in results:
        all_cats.update(cat_score_map(d).keys())

    if all_cats:
        print(f"  {'Category':<25}", end="")
        for lbl in labels:
            print(f"  {lbl[:col_w]:>{col_w}}", end="")
        print()
        print(f"  {'-'*25}", end="")
        for _ in labels:
            print(f"  {'-'*col_w}", end="")
        print()
        for cat in sorted(all_cats):
            print(f"  {cat:<25}", end="")
            for _, d in results:
                score = cat_score_map(d).get(cat)
                s = f"{score:.1f}" if score is not None else "—"
                print(f"  {s:>{col_w}}", end="")
            print()
        print()

    # Test count
    print(f"  {'Tests run':<25}", end="")
    for _, d in results:
        print(f"  {len(d.get('tests', [])):>{col_w}}", end="")
    print()

    # Per-test score comparison (by test id)
    all_ids: list[str] = []
    seen: set[str] = set()
    for _, d in results:
        for t in d.get("tests", []):
            tid = t.get("id") or t.get("name", "?")
            if tid not in seen:
                all_ids.append(tid)
                seen.add(tid)

    if all_ids:
        print()
        print(f"  {'Test':<30}", end="")
        for lbl in labels:
            print(f"  {lbl[:col_w]:>{col_w}}", end="")
        print()
        print(f"  {'-'*30}", end="")
        for _ in labels:
            print(f"  {'-'*col_w}", end="")
        print()
        for tid in all_ids:
            print(f"  {tid:<30}", end="")
            for _, d in results:
                idx = {(t.get("id") or t.get("name")): t for t in d.get("tests", [])}
                t = idx.get(tid)
                if t is None:
                    print(f"  {'—':>{col_w}}", end="")
                else:
                    score = t.get("score")
                    status = t.get("status", "?")
                    s = f"{score:.2f}/{status}" if score is not None else status
                    print(f"  {s[:col_w]:>{col_w}}", end="")
            print()

    print()
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
