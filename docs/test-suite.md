# Test Suite Contributor Guide

Reference for writing and validating test definitions in `tests/`.

---

## How tests are loaded

`tools/bench_suite.py` walks `tests/<category>/*.yaml` (recursively, alphabetical order within each directory). Files under `tests/agentic/fixtures/` and `tests/assets/` are skipped — those are referenced by tests, not loaded as tests.

Every file is validated against `schema/test-v1.schema.json` at load time. A file that fails validation aborts the run before any model calls are made. The file's stem (basename without `.yaml`) must match the `id` field exactly.

Categories run in this order: basic, tool_use, instruction, file_ops, coding, long_context, reasoning, writing, research, agentic.

---

## Required fields

Every test YAML must have these fields:

| Field         | Type   | Notes |
|---------------|--------|-------|
| `id`          | string | Must match the filename stem. Lowercase, hyphens OK. |
| `name`        | string | Human-readable display name. |
| `category`    | string | One of the 10 categories above. |
| `grader`      | string | One of the registered grader names. |
| `timeout_sec` | int    | Wall-clock budget for this test. |
| `prompt`      | string | Used by most graders. |

Agentic tests use `task_prompt` instead of `prompt`, and require `fixture` and `frameworks` too (see agentic grader section below).

Optional fields used by some graders:
- `prompt_template` — like `prompt` but may contain `{{ asset:filename }}` substitutions.
- `grader_config` — grader-specific dict (described per grader below).
- `max_score` — defaults to 1.0; used if a test can score fractionally with a different maximum.

---

## Asset substitution

Any string field that appears in the test YAML (including `prompt`, `prompt_template`, `task_prompt`) can reference files under `tests/assets/`:

```
{{ asset:haystack-16k.txt }}
```

The runner replaces that token with the file's full text content before passing it to the grader. Missing assets produce a `[missing asset: <name>]` placeholder and the test is likely to fail but won't abort the run.

This is the mechanism used by `needle` tests to inject large haystacks without embedding them in the YAML.

---

## Per-grader reference

### `exact_match`

Normalized string equality against a known answer.

**grader_config fields:**

| Field             | Type    | Default | Notes |
|-------------------|---------|---------|-------|
| `expected_answer` | string  | required | The correct answer. |
| `case_sensitive`  | bool    | `false` | If false, both sides are lowercased. |
| `strip`           | bool    | `true`  | Strip leading/trailing whitespace before compare. |

**details shape:** `{expected, got, matched}`

**Example:**

```yaml
id: basic-capital-france
name: Capital of France
category: basic
grader: exact_match
timeout_sec: 30
prompt: "What is the capital of France? Reply with the city name only."
grader_config:
  expected_answer: Paris
```

---

### `contains`

Case-insensitive substring check. All `must_contain` strings must appear; none of `must_not_contain` may appear.

**grader_config fields:**

| Field              | Type       | Default | Notes |
|--------------------|------------|---------|-------|
| `must_contain`     | list[str]  | `[]`    | All must be present in response. |
| `must_not_contain` | list[str]  | `[]`    | None may be present. |

**details shape:** `{missing, forbidden}`

**Example:**

```yaml
id: basic-greeting
name: Greeting contains hello
category: basic
grader: contains
timeout_sec: 30
prompt: "Say hello to the user."
grader_config:
  must_contain:
    - hello
  must_not_contain:
    - goodbye
```

---

### `regex`

`re.search` against the response. Optional negative patterns.

**grader_config fields:**

| Field            | Type       | Default | Notes |
|------------------|------------|---------|-------|
| `pattern`        | string     | required | Python `re` pattern. |
| `flags`          | list[str]  | `[]`    | `"IGNORECASE"`, `"MULTILINE"`, `"DOTALL"`. |
| `must_not_match` | list[str]  | `[]`    | Patterns that cause failure if matched. |

**details shape:** `{pattern, matched}` or `{pattern, matched, violated_must_not}`

**Example:**

```yaml
id: instruction-bullet-list
name: Response must use bullet points
category: instruction
grader: regex
timeout_sec: 45
prompt: "List three benefits of exercise. Use bullet points (- or *)."
grader_config:
  pattern: "^[-*]"
  flags:
    - MULTILINE
```

---

### `tool_call`

OpenAI function-calling correctness. Three modes: `single`, `dual`, `restraint`.

**grader_config fields (all modes):**

| Field   | Type       | Default    | Notes |
|---------|------------|------------|-------|
| `tools` | list[dict] | `[]`       | OpenAI tool schema array passed to the model. |
| `mode`  | string     | `"single"` | `single`, `dual`, or `restraint`. |

**Mode `single` — additional fields:**

| Field                    | Type   | Notes |
|--------------------------|--------|-------|
| `expected_tool`          | string | Tool name that must be called. |
| `expected_param_key`     | string | Argument key to inspect. |
| `expected_param_contains`| string | Substring that must appear in the argument value. |

**Mode `dual` — additional fields:**

| Field            | Type      | Notes |
|------------------|-----------|-------|
| `expected_tools` | list[str] | All named tools must be called. |

**Mode `restraint` — additional fields:**

| Field             | Type   | Notes |
|-------------------|--------|-------|
| `expected_answer` | string | Optional substring that should appear in the text response. |

Restraint mode passes (1.0) if no tool is called and the expected answer is present, scores 0.5 if no tool is called but the answer is missing, and 0.0 if any tool is called.

**details shape:** `{mode, tool_calls, matched, reason?}`

**Example (single):**

```yaml
id: tool-weather-single
name: Weather tool single call
category: tool_use
grader: tool_call
timeout_sec: 45
prompt: "What's the weather in Paris right now?"
grader_config:
  mode: single
  expected_tool: get_weather
  expected_param_key: location
  expected_param_contains: paris
  tools:
    - type: function
      function:
        name: get_weather
        description: Get current weather for a location
        parameters:
          type: object
          properties:
            location:
              type: string
          required: [location]
```

---

### `needle`

Needle-in-a-haystack for long context. The grader loads a text asset, injects a unique phrase at the specified depth, and checks whether the model can retrieve it.

**grader_config fields:**

| Field            | Type   | Default | Notes |
|------------------|--------|---------|-------|
| `haystack_asset` | string | required | Filename under `tests/assets/`. |
| `needle`         | string | required | Unique phrase to inject. |
| `depth`          | float  | `0.5`   | Fractional position (0.0=start, 1.0=end). |
| `question`       | string | required | What to ask about the needle. |
| `expected_answer`| string | required | Substring that must appear in the response. |

Score is 1.0 if `expected_answer` is found in the response, else 0.0.

**details shape:** `{haystack_chars, depth, needle, matched}`

**Example:**

```yaml
id: long-context-needle-4k
name: Needle in 4K haystack
category: long_context
grader: needle
timeout_sec: 120
prompt: ""   # unused; grader builds its own prompt
grader_config:
  haystack_asset: haystack-4k.txt
  needle: "The secret code word is ZEPHYR-9."
  depth: 0.5
  question: "What is the secret code word?"
  expected_answer: ZEPHYR-9
```

Note: `prompt` is required by the schema but ignored by this grader; set it to empty string.

---

### `file_check`

Asks the model to produce file contents; writes the response to disk; checks filesystem state.

**grader_config fields:**

| Field              | Type       | Notes |
|--------------------|------------|-------|
| `write_response_to`| string     | Relative path (under work dir) to write the raw response. |
| `file_checks`      | list[dict] | List of check objects. |

Each check object:

| Field               | Type      | Notes |
|---------------------|-----------|-------|
| `path`              | string    | Relative path under work dir to inspect. |
| `must_exist`        | bool      | Check file exists. |
| `must_contain`      | list[str] | Each string must appear in file content. |
| `forbidden_content` | list[str] | None may appear in file content. |

Score = fraction of checks that pass.

**details shape:** `{checks: [{path, passed, reasons}], passed, total}`

**Example:**

```yaml
id: file-ops-gitignore
name: Generate .gitignore for Python
category: file_ops
grader: file_check
timeout_sec: 60
prompt: |
  Generate a .gitignore file for a Python project. Output only the file
  contents, no explanation or code fences.
grader_config:
  write_response_to: .gitignore
  file_checks:
    - path: .gitignore
      must_exist: true
      must_contain:
        - __pycache__
        - "*.pyc"
      forbidden_content:
        - "```"
```

---

### `exec_unit_tests`

Prompts the model to write code; extracts the code block; runs it against unit test cases. Score = fraction of passing tests.

**grader_config fields:**

| Field        | Type                              | Default         | Notes |
|--------------|-----------------------------------|-----------------|-------|
| `language`   | string                            | `"python"`      | `python`, `javascript`, `bash`, `sql`, `go`. |
| `entrypoint` | string                            | `"main"`        | Function name (Python/JS/Go). Ignored for bash/SQL. |
| `unit_tests` | list[dict]                        | `[]`            | Test cases (see below). |
| `scoring`    | string                            | `"per_test_case"` | Only mode in v1. |
| `schema`     | string                            | `""`            | SQL only: DDL to set up tables before running queries. |

Unit test case shape (Python/JS/Go): `{input: [...args], expected: <value>}`
Bash: `{input: [...args], expected: "<stdout>"}`
SQL: `{expected: [[row1col1, ...], ...]}`

Missing runtime (no `node`, `python3`, etc.) → status `skipped`.

**details shape:** `{language, passed, total, per_test, error?}`

**Example:**

```yaml
id: coding-fizzbuzz
name: FizzBuzz implementation
category: coding
grader: exec_unit_tests
timeout_sec: 60
prompt: |
  Write a Python function called `fizzbuzz(n)` that returns the FizzBuzz
  string for n: "Fizz" if divisible by 3, "Buzz" if by 5, "FizzBuzz" if
  both, else the number as a string.
grader_config:
  language: python
  entrypoint: fizzbuzz
  unit_tests:
    - input: [1]
      expected: "1"
    - input: [3]
      expected: Fizz
    - input: [5]
      expected: Buzz
    - input: [15]
      expected: FizzBuzz
```

---

### `llm_judge`

Calls an external judge model to score the response against a rubric. Returns the mean (or weighted mean) of numeric fields in the judge's JSON response.

Requires `--judge-url` and `--judge-model` at runner invocation. If no judge is configured, the test is skipped (status `skipped`, score `0.0` excluded from denominator).

**grader_config fields:**

| Field                 | Type   | Default  | Notes |
|-----------------------|--------|----------|-------|
| `judge_rubric`        | string | required | Instruction sent to the judge. Must ask for JSON with numeric fields. |
| `judge_aggregation`   | string | `"mean"` | `"mean"` or `"weighted"`. |
| `judge_weights`       | dict   | `null`   | Required if aggregation=weighted. Keys are rubric dimension names. |
| `judge_temperature`   | float  | `0.0`    | Judge model temperature. |
| `judge_max_retries`   | int    | `2`      | Retries on JSON parse failure. |

The judge is called with `temperature=0.0` and `response_format={"type": "json_object"}`. Scores must be in 0.0–1.0 range; values outside are clamped.

**details.judge shape:** `{model_response, rubric_scores, rationale, judge_raw}`

**Example:**

```yaml
id: reasoning-logic-puzzle
name: Logic puzzle reasoning quality
category: reasoning
grader: llm_judge
timeout_sec: 120
prompt: |
  A farmer has a fox, a chicken, and a bag of grain. He needs to cross a
  river in a boat that holds only him and one item. The fox eats the chicken
  if left alone; the chicken eats the grain. How does he cross?
grader_config:
  judge_rubric: |
    Score the response on these dimensions from 0.0 to 1.0:
    - correctness: Does it solve the puzzle correctly?
    - clarity: Is the solution explained clearly?
    - completeness: Are all three crossings described?
    Return JSON only: {"correctness": 0.0, "clarity": 0.0, "completeness": 0.0, "rationale": "..."}
```

---

### `agentic`

Runs the task across 1–3 agent frameworks (opencode, aider, custom) against a seed git fixture. Each framework run produces a separate result row. The runner calls `grade_multi()` directly — the `agentic` grader entry in the registry exists only for consistency.

**Top-level test fields (in addition to required):**

| Field        | Type      | Notes |
|--------------|-----------|-------|
| `fixture`    | string    | Directory name under `tests/agentic/fixtures/`. |
| `task_prompt`| string    | What to tell the agent. `prompt` field is not used. |
| `frameworks` | list[str] | Subset of `["opencode", "aider", "custom"]`. |

**grader_config fields:**

| Field            | Type       | Notes |
|------------------|------------|-------|
| `setup_commands` | list[str]  | Shell commands run in the work dir before the agent (120s timeout). |
| `success_check`  | dict       | `{command: str, max_diff_lines?: int}`. Exit 0 = full score. |
| `partial_credit` | list[dict] | Each: `{check: str, points: float}`. Independent checks. |
| `cleanup`        | string     | Only `"always"` supported in v1. |

Score for each framework: 1.0 if `success_check` exits 0; else sum of partial_credit points (capped at 1.0); timeout runs still attempt partial credit.

See `docs/agentic-harness.md` for fixture layout, timeout policy, and opencode spike notes.

**Example:**

```yaml
id: agentic-add-type-hints
name: Add type hints to Python module
category: agentic
grader: agentic
timeout_sec: 300
fixture: python-no-hints
task_prompt: "Add type hints to all functions in utils.py. Do not change any logic."
frameworks:
  - aider
  - custom
grader_config:
  success_check:
    command: "python3 -c 'import ast, sys; ast.parse(open(\"utils.py\").read())'"
  partial_credit:
    - check: "grep -q ':' utils.py"
      points: 0.5
  cleanup: always
```

---

## Adding a test

1. **Pick a category.** Choose the category whose grader best matches what you're testing. If you need judge scoring, use `reasoning`, `writing`, or `research`. If you need code execution, use `coding`. For agentic multi-step tasks, use `agentic`.

2. **Write the YAML.** Create `tests/<category>/<id>.yaml`. The filename stem must match `id`. Follow the grader's required fields above.

3. **Validate.**
   ```bash
   python3 tools/validate.py --tests tests/
   ```
   This runs schema validation on every test YAML. Fix any reported errors before proceeding.

4. **Smoke-test against a dev endpoint.**
   ```bash
   python3 tools/bench_suite.py \
     --url http://127.0.0.1:4000 --api-key "$API_KEY" \
     --model "your-model" --engine vllm \
     --foundation dev --hardware cpu \
     --categories <your-category>
   ```
   Check that the test runs, scores sensibly, and produces a valid result JSON.

5. **Check the result.** For llm_judge tests, inspect `details.judge.rubric_scores` to confirm the judge is responding correctly. For exec_unit_tests, inspect `details.per_test` to see which cases passed/failed.

6. **Add assets if needed.** Long text files (haystacks, reference documents) go in `tests/assets/`. Reference them with `{{ asset:filename }}` in the YAML.

7. **Commit.** Add the YAML (and any new assets) and open a PR. CI runs `python3 tools/validate.py --tests tests/` as a gate.
