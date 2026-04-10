# Agentic Harness

Reference for the `agentic` grader: the 3-framework model, timeout policy, fixture layout, and how to add and maintain agentic tests.

---

## The 3-framework model

Each agentic task runs independently against three agent frameworks:

| Framework | Runner | What it contributes |
|-----------|--------|---------------------|
| `opencode` | `tools/agents/opencode_runner.py` | A purpose-built coding agent with its own tool loop and context management. Tests whether a full agentic coding tool can follow the task. |
| `aider`    | `tools/agents/aider_runner.py`    | A mature, widely-deployed code-editing agent. Provides a stable baseline; well-understood failure modes. |
| `custom`   | `tools/agents/custom_loop.py`     | A minimal single-turn loop that calls the target model directly via `ModelClient`. Tests whether the raw model (without a framework) can follow instructions. |

**Why three frameworks?** The spread lets you distinguish two types of failure:

- **Model problem**: all three frameworks fail. The model cannot follow the task instructions regardless of scaffolding.
- **Framework problem**: one or two frameworks fail while others pass. The model is capable, but one framework's prompt construction, context handling, or tool use is breaking.

This signal is especially useful when evaluating models for use with a specific agent framework (e.g., deciding whether to adopt opencode in a production pipeline).

Per-framework result rows appear in the result JSON with `agent_framework` set to the framework name. The `agent_framework_scores` summary aggregates across tasks per framework.

---

## Timeout policy

Each framework run gets the full `timeout_sec` budget specified in the test YAML. This is a wall-clock budget — the runner does not adjust for CPU vs GPU.

**Why not shorter on CPU?** Agentic tasks involve multi-turn reasoning and file edits. A timeout that's tight on CPU will produce misleading results (apparent task failures that are actually infrastructure slowness). Use the same `timeout_sec` across foundations; the elapsed time recorded in the result JSON lets you analyze the timing difference separately.

**SIGKILL on timeout:** When a framework run exceeds its budget, the runner sends SIGKILL to the entire process group (`os.killpg`). This ensures no orphan subprocesses (git, pip, node, etc.) survive. The agentic grader uses `preexec_fn=os.setsid` when launching agent processes so they form their own session group.

**Partial credit on timeout:** A timed-out run is not automatically scored 0.0. The grader still runs the `partial_credit` checks against whatever state the work directory is in. If the agent got halfway through the task before timing out, it earns those points. The result row has `status=timeout` with `partial_credit_score` in details.

---

## Fixture layout

Agentic tests operate against a git repository pre-populated with source code. Fixtures live in `tests/agentic/fixtures/<fixture-name>/`.

**The `.git-seed/` convention:**

You cannot check a `.git/` directory into git (nested git repos confuse the outer repo). Instead, store a minimal git object store in `.git-seed/`:

```
tests/agentic/fixtures/python-no-hints/
├── utils.py           # source file with no type hints
├── README.md          # task context
└── .git-seed/         # renamed from .git/ before committing
    ├── config
    ├── HEAD
    └── objects/
```

When the grader sets up a framework run, it:
1. Copies the fixture directory to a temp work dir.
2. Renames `.git-seed/` to `.git/`.
3. Runs `git init -q` (idempotent — fills in missing refs).

The agent then sees a clean git repository it can read, commit to, and diff against.

**Creating a fixture from an existing repo:**

```bash
# From your fixture source directory
mv .git .git-seed
# Commit to tests/agentic/fixtures/<name>/
git add tests/agentic/fixtures/<name>/
```

**Fixtures with no git history:** If you just need a directory of files and don't care about git history (e.g., the success check doesn't use `git diff`), you can omit `.git-seed/`. The grader will still run `git init -q` and the framework will start with an empty commit history.

---

## Adding a new agentic test

1. **Create the fixture.**
   ```bash
   mkdir -p tests/agentic/fixtures/<my-fixture>
   # Copy in source files
   cd tests/agentic/fixtures/<my-fixture>
   git init && git add . && git commit -m "init"
   mv .git .git-seed
   ```

2. **Write the YAML** at `tests/agentic/<my-test-id>.yaml`:
   ```yaml
   id: agentic-my-task
   name: My agentic task description
   category: agentic
   grader: agentic
   timeout_sec: 300
   fixture: my-fixture
   task_prompt: |
     Describe the task precisely. Agents read this as their instruction.
   frameworks:
     - aider
     - custom
   prompt: ""   # required by schema, unused by agentic grader
   grader_config:
     setup_commands:
       - pip install -q -r requirements.txt   # if needed
     success_check:
       command: "python3 -m pytest tests/ -q"
       max_diff_lines: 500
     partial_credit:
       - check: "python3 -c 'import ast; ast.parse(open(\"module.py\").read())'"
         points: 0.3
       - check: "grep -q 'def ' module.py"
         points: 0.2
     cleanup: always
   ```

3. **Validate:**
   ```bash
   python3 tools/validate.py --tests tests/
   ```

4. **Smoke-test locally** with `--categories agentic --no-interactive`. Inspect the result for each framework's `status` and `details`.

5. **Commit** fixture and YAML together.

---

## Version-bumping frameworks

Each framework runner is a single file:

| Framework | Runner file | Requirements |
|-----------|-------------|--------------|
| opencode  | `tools/agents/opencode_runner.py` | `opencode` binary on PATH |
| aider     | `tools/agents/aider_runner.py`    | `tools/agents/requirements.txt` |
| custom    | `tools/agents/custom_loop.py`     | none (uses `ModelClient`) |

To bump `aider`:
1. Update the version pin in `tools/agents/requirements.txt`.
2. Run `pip install -r tools/agents/requirements.txt` in your test environment.
3. Run `python3 tools/bench_suite.py --categories agentic ...` against at least two fixtures.
4. Check that scores are stable (aider outputs are deterministic given the same model and temperature).

When bumping aider, inspect any agentic test that was previously passing to verify it still passes. A score drop usually means a prompt-format change in the new version — update the `task_prompt` field in the affected YAML if needed.

**What to verify after any framework bump:**
- All agentic fixtures still set up without error (`status != "error"` for setup).
- At least one task scores > 0.0 per framework (proves the framework is functional).
- No leftover work directories under `.bench-work/` (cleanup is working).

---

## Opencode spike notes

**The `opencode_runner.py` is scaffolded but not yet validated against a real opencode install.**

The scaffolded CLI invocation in `opencode_runner.py` is:

```bash
opencode run \
  --model <model_name> \
  --api-base <url> \
  --api-key <key> \
  --no-interactive \
  "<task_prompt>"
```

This is a reasonable guess based on opencode's documented CLI, but it has not been tested against an actual opencode binary. The runner checks `shutil.which("opencode")` first and returns `status=error` with `error="opencode not installed"` if the binary is missing — so running without opencode installed is safe.

See the `TODO(spike)` comment in `tools/agents/opencode_runner.py`.

**If the spike reveals that `--no-interactive` does not work:**

Drop `opencode` from the default `frameworks:` list in any affected agentic test YAML files. The default in the grader is `["opencode", "aider", "custom"]`, but each test can override with a subset. `aider` + `custom` provide sufficient signal for the model vs. framework distinction.

Example override in a test YAML:
```yaml
frameworks:
  - aider
  - custom
```

This is the recommended fallback if opencode's non-interactive mode turns out to be unviable. Update this document once the spike is completed.
