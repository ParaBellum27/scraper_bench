# Agent harness

Mistral and Gemini can run through their official terminal clients, with only the benchmark's sandboxed Python tool exposed over MCP. The direct Mistral API runner remains available. OpenAI browser trials are separate. These evaluate model-plus-agent setups, not controlled model-only differences.

## Model-side environment

The model receives:
- the task prompt;
- one editable `solution.py` file;
- one logical tool: `run_solution(code)`, which overwrites `solution.py` and executes it with public JSON stdin.

The model does **not** receive the hidden grader, reference implementation, hidden scenarios, or hidden-test results.

## Execution-side environment

During development, the runner creates a temporary workspace outside the repository containing only `task.md`, the task's workbook, and `inputs/base_case.json`. The public workbook name defaults to `fcff2st.xlsx`; set `--workbook-name` for another task. The model must write Python to inspect these artifacts. Every tool call replaces `solution.py`; the last saved file becomes the frozen submission.

Execution requires macOS `sandbox-exec` and fails closed elsewhere. The profile permits public-workspace reads/writes and runtime/library reads, and configures denial of external files, network access, and process forking. Candidate environment construction excludes provider credentials. Output capture is bounded to 64 KiB per stream. Tests exercised private-file/symlink/network denial, time/output limits, and fresh grading state; direct fork denial and seeded credential-canary checks are not recorded. See the [tested-controls and limitations matrix](../BENCHMARK_SUMMARY.md#c-leakage-grading-exploits-and-evidence-gaps).

At final grading, each case runs in a fresh sandbox workspace containing only a copy of `solution.py`. The workbook, public input files, and previous-case scratch are unavailable. Inputs arrive only over stdin.

## Fairness controls

Default limits:
- 20 model turns;
- 12 `run_solution` calls;
- 10 seconds per execution call;
- direct Mistral API runner: temperature 0 and at most 8,192 completion tokens per turn;
- no internet inside the code-execution sandbox.

The terminal runner also enforces a 900-second overall deadline. Native CLI turn semantics and generation defaults differ: Vibe uses temperature 1 and high thinking; Gemini uses its CLI defaults. Both receive the same public artifacts and Python execution budget. The MCP execution count and original public stdin survive server restarts. CLI failures are incomplete attempts, not model scores; a successful CLI exit still requires a saved candidate. Only public feedback reaches the model.

## Secrets

Set API keys locally; never commit them:

```bash
export MISTRAL_API_KEY="..."
export GEMINI_API_KEY="..."
```

Direct-API model defaults are in `harness/config.py`; terminal defaults and isolated client settings are in `harness/providers/{mistral,gemini}_cli.py`.

The runners use the repository's local `.env` without overriding exported keys. Terminal clients receive only the selected provider credential. `--mistral-auth-dir` explicitly selects an isolated Vibe account credential instead of the Studio key. Candidate Python processes receive neither credential.

## Direct Mistral API trial

From the repository root, using the existing virtualenv:

```bash
.venv/bin/python -m harness.run_benchmark \
  --provider mistral \
  --model mistral-medium-3-5 \
  --workbook /absolute/path/to/fcff2st.xlsx
```

The runner prints a unique `runs/private/mistral-...` directory. It saves:
- `trajectory.json`: full model responses, tool arguments, public execution results, and stop reason;
- `step-*-call-*.py`: source submitted at each execution;
- `solution.py`: the frozen candidate file, without human corrections;
- `metadata.json`: limits, requested/returned models, token usage, timestamps, and public-artifact/submission SHA-256 hashes.

Grade the frozen file separately; never feed hidden results back into that attempt:

```bash
.venv/bin/python -m evaluator.run_grader \
  runs/private/mistral-RUN_TIMESTAMP/solution.py \
  --seed 20261003 \
  > runs/private/mistral-RUN_TIMESTAMP/grade.json
```

All raw artifacts under `runs/` are ignored by Git. An API or harness failure is recorded as `failed`, not reported as a model score. The [curated evidence pack](../results/damodaran_fcff2st/pilot-2026-10-04/README.md) contains sanitized historical results and credential-free offline replay commands.

If generation returns HTTP 429 (`rate_limited`, code `1300`), successful model listing does not establish available completion quota. Check the account's [API Limits](https://admin.mistral.ai/plateforme/limits) and [Usage](https://admin.mistral.ai/organization/usage). The runner records the error without automatically retrying or switching models. A failed request that produces no submission has no benchmark score.

## Official terminal trials

Supported client configuration: Vibe 2.25.8 and Gemini CLI 0.29.5. Install with `uv tool install mistral-vibe==2.25.8` and `npm install -g @google/gemini-cli@0.29.5`.

The Python runtime needs the repository requirements, including `mcp==1.30.0` and `openpyxl`. A runtime outside Desktop avoids the slow package-file reads observed in the repository virtualenv:

```bash
# One-time setup for a new runtime; reuse it thereafter.
uv venv --python 3.13 "$HOME/.local/share/scraper-bench/runtime"
uv pip install --python "$HOME/.local/share/scraper-bench/runtime/bin/python" -r requirements.txt
```

Run from the repository root:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PY" -m harness.run_terminal \
  --provider gemini --model gemini-3.8-flash \
  --workbook /absolute/path/to/fcff2st.xlsx

"$PY" -m harness.run_terminal \
  --provider mistral --model mistral-medium-3.5 \
  --mistral-auth-dir runs/private/mistral-cli-auth \
  --workbook /absolute/path/to/fcff2st.xlsx
```

The two commands may run in separate terminals concurrently; their workspaces, client homes, counters, and result directories are independent. Each verifies sandboxed workbook loading before consuming inference quota. Native shell/file/web tools, subagents, extensions, project context, and connectors are disabled.

Vibe advertises `mistral-medium-3.5` as Mistral Medium 3.5 and maps it to `mistral-vibe-cli-latest`. This is not the direct API identifier `mistral-medium-3-5`. Metadata records both selections. Gemini events/native sessions record selected request models; Vibe's public event stream does not expose a resolved backend model revision. Do not claim either alias pins an immutable backend revision.

For an initial Vibe account login, use an isolated credential directory:

```bash
env -u MISTRAL_API_KEY \
  VIBE_HOME="$PWD/runs/private/mistral-cli-auth" \
  VIBE_TEST_DISABLE_KEYRING=1 vibe --setup
```

This official flow may open a browser once; benchmark execution itself is terminal-only. The keyring-disabling setting keeps the provisioned credential in that directory's private `.env`, rather than modifying the global Keychain. Never publish it. Studio and account-backed inference can have different access: the observed Studio key rejected Medium while account-backed Vibe accepted it. A browser approval page alone is not proof that the CLI completed credential exchange. In the pilot, default three-second auth polling hit HTTP 429; a temporary launcher using the official auth service's twelve-second polling interval completed login. That launcher was removed, not installed as a permanent client modification.

Terminal runs save:
- `cli-events.jsonl` and `cli-stderr.txt`: native trajectory and diagnostics, including failed attempts;
- `step-*.py` and `executions.jsonl`: exact submitted code and public execution results;
- `metadata.json`: client version, model selection, authentication route (not the key), limits, status, usage when emitted, and artifact hashes;
- non-secret client settings and, when emitted, Gemini `native-sessions/` transcripts;
- `solution.py` only after successful freezing; `partial-solution.py` preserves an incomplete candidate when available.

The earliest Gemini pilot predates native-session/settings preservation; its native stdout trajectory remains available. Grade a frozen terminal submission with the same `evaluator.run_grader` command above, using the chosen runtime. Never send hidden grading results back into that run.

### Repeating the recorded local condition

The original public bundle is preserved locally at `runs/private/frozen-public-inputs/`. Its hashes match the scored pilots; the Desktop workbook changed afterward and was not overwritten. Use all three frozen artifacts for comparable reruns:

The frozen artifacts preserve the public inputs, not later harness source changes. The pre-Pierre publication snapshot is `c58ca03ef26b80b22f2fa137919221c31791a600`; its manifest records publication-time source hashes, not immutable per-run build provenance. The new generic workbook support changes the MCP tool description even though the default system prompt and historical grading results remain unchanged.

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
PUBLIC="runs/private/frozen-public-inputs"
"$PY" -m harness.run_terminal \
  --provider gemini --model gemini-3.8-flash \
  --task "$PUBLIC/task.md" \
  --base-input "$PUBLIC/inputs/base_case.json" \
  --workbook "$PUBLIC/fcff2st.xlsx"
```

The last Gemini recovery reported daily API quota exhaustion (20 requests) and a retry time around `2026-10-05T00:00:00Z`. The user chose to retain this API condition and wait for reset, not install a different client or change billing. No overnight run was scheduled. A turn budget is not an API quota guarantee: native clients may issue internal retries, and failed attempts must remain recorded separately from model scores.

An existing Google-account credential authenticated but the legacy Gemini CLI rejected its consumer entitlement. Google's [migration announcement](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) documents that retirement. Antigravity CLI was researched but not installed or substituted; its account model selector and agent setup would be a separate condition requiring explicit validation.

### Design references

The one host-owned MCP tool follows [Inspect's Agent Bridge](https://inspect.aisi.org.uk/agent-bridge.html) boundary. Frozen artifact handoff follows [Harbor's separate verifier](https://docs.harborframework.com/tasks/separate-verifier.md); native transcript retention follows its [Gemini adapter](https://github.com/harbor-framework/harbor/blob/main/src/harbor/agents/installed/gemini_cli.py). These patterns do not remove provider entitlement or quota requirements.

## Pierre LBO One

Use the qualified derivative, never the author's original or its stale cached results. The checked-in public files are the frozen version-0.1 bundle; local identical copies are under `runs/private/pierre_lbo/frozen-public/`. Their hashes are in `tasks/pierre_lbo/metadata.json`. These commands preserve the existing client, model, authentication and budget conditions:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
PUBLIC="tasks/pierre_lbo"
"$PY" -m harness.run_terminal \
  --provider mistral --model mistral-medium-3.5 \
  --mistral-auth-dir runs/private/mistral-cli-auth \
  --task "$PUBLIC/task.md" --base-input "$PUBLIC/inputs/base_case.json" \
  --workbook "$PUBLIC/pierre_lbo_one.xlsx" --workbook-name pierre_lbo_one.xlsx

# Run only when the recorded Gemini API quota condition is available again.
"$PY" -m harness.run_terminal \
  --provider gemini --model gemini-3.8-flash \
  --task "$PUBLIC/task.md" --base-input "$PUBLIC/inputs/base_case.json" \
  --workbook "$PUBLIC/pierre_lbo_one.xlsx" --workbook-name pierre_lbo_one.xlsx
```

Grade the actual frozen submission path printed by the runner:

```bash
"$PY" -m evaluator.run_grader runs/private/RUN_DIRECTORY/solution.py \
  --benchmark pierre_lbo --seed 20261004
```

Read `hidden_cases_fully_correct` and per-field mismatches, not just the overall score or `hidden_cases_passed_95`. Keep all hidden feedback out of generation. The direct API runner accepts the same public task/base/workbook/name flags, but its existing entitlement and generation-setting differences remain; do not substitute it as an equivalent Vibe condition.

To independently requalify the oracle, choose a new output directory so existing evidence is not overwritten:

```bash
SOFFICE="$HOME/.local/share/scraper-bench/tools/LibreOffice-26.8.0.app/Contents/MacOS/soffice"
"$PY" -m reference.pierre_lbo.qualify \
  --engine libreoffice --soffice "$SOFFICE" \
  --output-dir runs/private/pierre_lbo/new-qualification
```

Alternatively use `--engine excel` on macOS when Excel automation is accessible. It requests calculation only for the newly generated workbook's sheets; it does not change global calculation/alert settings or close/save unrelated books. Native Excel verification was blocked in this campaign; the recorded 46/46 result uses LibreOffice, with an isolated profile per conversion. See the [full qualification and limitations](../analysis/pierre_lbo_report.md).

The public workbook can be rebuilt from source with `python -m reference.pierre_lbo.workbook build --inputs tasks/pierre_lbo/inputs/base_case.json --output /new/path/pierre_lbo_one.xlsx`, then recalculated. Rebuilding is not a byte-identical substitute for the frozen campaign bundle: use the same frozen files for competing trials.


## Local verification

```bash
"$HOME/.local/share/scraper-bench/runtime/bin/python" -m unittest discover -s tests -v
```

The macOS regressions exercise stdin, scratch writes, denied private/symlink/network access, execution limits, fresh grading workspaces, MCP restart budgets/input integrity, and rejection of forbidden tools/model changes. Real MCP stdio and native CLI pilots exercise the integration beyond these tests. A reference smoke run is infrastructure verification, not a candidate score.
