#!/usr/bin/env node
// Sandboxed JS execution helper for exec_unit_tests grader.
// Usage: node sandbox_runner.js <candidate_file> <entrypoint> <test_cases_json>
// Same contract as sandbox_runner.py.

const fs = require('fs');
const path = require('path');

function match(got, expected, expectedLength) {
  if (expectedLength !== undefined && expectedLength !== null) {
    try { return got.length === expectedLength; } catch { return false; }
  }
  return JSON.stringify(got) === JSON.stringify(expected);
}

function main() {
  const [, , file, entrypoint, casesJson] = process.argv;
  if (!file || !entrypoint || !casesJson) {
    console.log(JSON.stringify({ passed: 0, total: 0, error: "usage: sandbox_runner.js <file> <fn> <cases>" }));
    return;
  }
  const cases = JSON.parse(casesJson);
  let mod;
  try {
    mod = require(path.resolve(file));
  } catch (e) {
    console.log(JSON.stringify({ passed: 0, total: cases.length, error: `import failed: ${e.message}` }));
    return;
  }
  const fn = mod[entrypoint] || (typeof mod === 'function' ? mod : null);
  if (typeof fn !== 'function') {
    console.log(JSON.stringify({ passed: 0, total: cases.length, error: `entrypoint ${entrypoint} not found or not a function` }));
    return;
  }
  const perTest = [];
  let passed = 0;
  for (const c of cases) {
    const inp = c.input || [];
    try {
      const got = fn(...inp);
      const ok = match(got, c.expected, c.expected_length);
      perTest.push({ input: inp, ok, got: JSON.stringify(got).slice(0, 100) });
      if (ok) passed++;
    } catch (e) {
      perTest.push({ input: inp, ok: false, error: `${e.name}: ${e.message}`.slice(0, 200) });
    }
  }
  console.log(JSON.stringify({ passed, total: cases.length, per_test: perTest }));
}

main();
