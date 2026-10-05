# Agent harness

Pierre LBO uses guarded direct APIs for Groq, Gemini and Mistral. Official terminal clients remain available for the separate historical FCFF condition. Do not substitute a CLI/account-backed model for a direct-API target.

## Model-side environment

The model receives:
- the task prompt;
- one public workspace for workbook inspection and Python execution;
- one logical tool: `run_solution(code, submit=False)`. Inspection is the default; only `submit=True` selects a final program.

The model does **not** receive the hidden grader, reference implementation, hidden scenarios, or hidden-test results.

## Execution-side environment

During development, the runner creates a temporary workspace outside the repository containing only `task.md`, the task's workbook, and `inputs/base_case.json`. The public workbook name defaults to `fcff2st.xlsx`; set `--workbook-name` for another task. Each execution may replace the public scratch `solution.py`, but **only the last explicit `submit=True` call selects the submission**. The host captures the exact supplied source before execution, even on errors, in a separate private snapshot. Later inspection or candidate filesystem writes cannot alter it. Reserve one execution to submit; final chat is not submission. An attempt without an explicit submission is ungraded.

Execution requires macOS `sandbox-exec` and fails closed elsewhere. The allowlist permits the public workspace, interpreter-declared standard-library components, `openpyxl`/`et_xmlfile`, and required system libraries—not an entire virtualenv or runtime prefix. The repository is explicitly denied. Private snapshots and writable workspaces cannot overlap readable runtime paths. Candidate environment construction excludes provider credentials, inherited descriptors are closed, network access and process forking are denied, and output is bounded to 64 KiB per stream. Installed interpreter/package contents remain trusted runtime inputs and must not contain credentials; this is not protection against a maliciously modified interpreter.

At final grading, each case runs in a fresh sandbox workspace containing only a copy of `solution.py`. The workbook, public input files, and previous-case scratch are unavailable. Inputs arrive only over stdin.

## Fairness controls

Default limits:
- 20 model turns;
- 12 `run_solution` calls;
- 10 seconds per execution call;
- direct campaign: 4,096 output tokens per turn for all three targets; provider-default temperature and thinking, with overrides omitted;
- no internet inside the code-execution sandbox.

Both direct and terminal runners enforce a 900-second overall generation deadline. The direct campaign additionally enforces persistent cumulative spend reservations, serial requests, pacing and bounded retries. Native CLI turn semantics and generation defaults differ: Vibe uses temperature 1 and high thinking; Gemini uses its CLI defaults. Historical CLI results therefore remain a separate condition.

## Secrets

The direct campaign reads each selected credential **only from the repository's current `.env`**, without exported-key fallback or `${...}` interpolation. Keys are passed privately to the pinned provider endpoint and never to candidate processes. Account confirmations are bound to a SHA-256 fingerprint of the current key in the private release record; rotation requires reconfirmation. No key values belong in artifacts or chat.

Historical terminal runners retain their documented environment/account-login routes. They are not an alternative way around direct campaign release or spending gates.

## Guarded direct API campaign

[`direct_policy.json`](direct_policy.json) pins `openai/gpt-oss-120b` on Groq, native `gemini-3.8-flash` on Gemini and `mistral-medium-latest` on Mistral. All use the same public v0.2 bundle, Python tool, explicit submission contract, 20 turns, 12 executions, 10-second executions and 4,096-token output cap. Native Gemini preserves thought signatures and uses documented `maxOutputTokens`; no temperature/thinking override or model fallback is applied.

From the repository root:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PY" -m harness.run_benchmark --provider groq --check
"$PY" -m harness.run_benchmark --provider gemini --check
"$PY" -m harness.run_benchmark --provider mistral --check
```

`--check` is the default and makes **no requests**. `--access-check` performs one small, capped `READY` probe after a real sandbox/workbook preflight, without starting a candidate. `--execute` repeats that probe immediately before one candidate trial; it requires separate candidate authorization. Generation never receives hidden feedback, reference code, scenarios or grading logic.

Private `runs/private/pierre_lbo/direct-api/release.json` records account confirmations, expiry, policy hash and distinct access-check/candidate authorization. A single `ledger.json` and exclusive `.lock` serialize **all three providers**, including access checks and retries. Never delete/reset the ledger, lock marker or provider trial-claim files to recover a budget. A crashed/failed claimed trial still consumes the one exploratory attempt.

Before dispatch, the ledger durably reserves the **maximum monetary cost**, using the hard model input ceiling and output allowance, not an estimated prompt token count. Gemini conservatively reserves its entire 65,536-token output ceiling, including thinking, even though the requested cap is lower. Valid usage settles down to actual token-priced cost; ambiguous errors, interruptions and missing/inconsistent usage retain the full hold. Exact integer accounting prevents rounding overspend. These are token-price bounds, not independent verification of provider billing or external account activity.

- Groq: confirmed free-only account, $0 cash spend; 30 RPM, 8,000 combined TPM, 1,000 RPD, 200,000 TPD.
- Gemini: confirmed Default Gemini Project, Tier 1; cumulative $2 including checks/retries; 1,000 RPM, 2 million input TPM, 10,000 RPD.
- Mistral: exclusively reserved $10 included allowance, $0 additional cash spend; requests evenly spaced at least one second, 20,000 combined TPM. Unknown daily quota is not assumed unlimited.

Quota estimates use full-payload `o200k_harmony` tokens plus 512 framing for Groq, and UTF-8 bytes/3 plus 512 for the others. They are **not billing bounds or guarantees against account-level 429s**. Groq's small window may stop a growing conversation before the turn budget; prompts/history are never silently trimmed. Actual usage reconciles rolling windows. Only 429 with a valid `Retry-After` can retry, at most twice, after another budget/deadline check. Ambiguous network/5xx failures are not automatically retried. Missing retry information triggers a conservative persisted cooldown.

The guard pins endpoints, disables redirects/ambient proxies, bounds response bytes and full network duration, and excludes response error bodies from logs. Installed runtimes and provider billing/usage reports remain trusted; unrelated account spending can invalidate an allowance reservation.

Each private run saves metadata, access-check response when available, accounting totals, raw candidate trajectory, protected execution snapshots and a hash-validated `solution.py` only after successful explicit submission. Access/quota/deadline/provider/protocol/truncation failures are separate from candidate tool/finance errors. No submission means ungraded. Effective defaults and backend revisions remain unavailable unless the provider exposes them.

Grade a successfully frozen candidate independently:

```bash
"$PY" -m evaluator.run_grader runs/private/pierre_lbo/direct-api/RUN/solution.py \
  --benchmark pierre_lbo --seed 20261004
```

Preparation evidence is in [`results/pierre_lbo/preparation-2026-10-05/`](../results/pierre_lbo/preparation-2026-10-05/). The earlier audit/trial plan is historical; its financial public hashes and qualification remain unchanged. Pricing sources and validity dates are embedded in the executable policy; expiry fails closed.

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
- `step-*.py`, `execution-state.json`, and `executions.jsonl`: exact executed code, explicit submission selection, and public execution results;
- `metadata.json`: client version, model selection, authentication route (not the key), limits, status, usage when emitted, and artifact hashes;
- non-secret client settings and, when emitted, Gemini `native-sessions/` transcripts;
- `solution.py` only after successful freezing of an explicit submission; failed attempts retain their host snapshots and selection state but are not silently graded.

The earliest Gemini pilot predates native-session/settings preservation; its native stdout trajectory remains available. Grade a frozen terminal submission with the same `evaluator.run_grader` command above, using the chosen runtime. Never send hidden grading results back into that run.

### Repeating the recorded local condition

The original public bundle is preserved locally at `runs/private/frozen-public-inputs/`. Its hashes match the scored pilots; the Desktop workbook changed afterward and was not overwritten. Use all three frozen artifacts for comparable reruns:

The frozen artifacts preserve the public inputs, not later harness source changes. The pre-Pierre publication snapshot is `c58ca03ef26b80b22f2fa137919221c31791a600`; its manifest records publication-time source hashes, not immutable per-run build provenance. The pretrial audit changes the shared prompt/tool contract to explicit submission; new runs are therefore a different harness version. Historical frozen submissions and their grading evidence are not rewritten.

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

Use the corrected derivative, never the author's original or stale caches. The audited public bundle and its hashes are recorded in `tasks/pierre_lbo/metadata.json`; the audit evidence and requested future execution condition are in [`results/pierre_lbo/audit-2026-10-05/`](../results/pierre_lbo/audit-2026-10-05/).

The three direct adapters, authoritative credential loading, shared deadline/rate/retry controls and persistent spend guards are now implemented; use the guarded campaign above. Account confirmations are private and key-bound. Access checks and candidate execution are separately authorized; benchmark qualification alone does not release either gate. The earlier [trial plan](../results/pierre_lbo/audit-2026-10-05/trial-plan.json) is retained as an immutable pre-implementation record.

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
```

Grade the actual frozen submission path printed by the runner:

```bash
"$PY" -m evaluator.run_grader runs/private/RUN_DIRECTORY/solution.py \
  --benchmark pierre_lbo --seed 20261004
```

The primary result is `hidden_cases_fully_correct` out of `hidden_cases_total` (45), with `all_hidden_cases_correct` and `all_cases_correct` flags. `score` is explicitly a weighted partial-credit diagnostic. Current reports no longer use the misleading 95-point pass count. Per-case `exercised_features` contain funded-period/output witnesses; a failed maturity obligation is not reported as a successful repayment. Keep all hidden feedback out of generation.

To independently requalify the oracle, choose a new output directory so existing evidence is not overwritten:

```bash
SOFFICE="$HOME/.local/share/scraper-bench/tools/LibreOffice-26.8.0.app/Contents/MacOS/soffice"
"$PY" -m reference.pierre_lbo.qualify \
  --engine libreoffice --soffice "$SOFFICE" \
  --output-dir runs/private/pierre_lbo/new-qualification
```

Rebuild deliberate-error controls from the current reference and grade them offline:

```bash
"$PY" -m reference.pierre_lbo.controls \
  --output-dir runs/private/pierre_lbo/new-controls
```

Qualification checks all 55 fields in the base plus all 45 hidden cases and separately recalculates the nine [hand-derived diagnostics](../reference/pierre_lbo/HAND_EXAMPLES.md). Diagnostic cases are not additional hidden scoring scenarios.

Alternatively use `--engine excel` on macOS when Excel automation is accessible. It requests calculation only for the newly generated workbook's sheets; it does not change global calculation/alert settings or close/save unrelated books. Native Excel verification was blocked in this campaign; the recorded 46/46 result uses LibreOffice, with an isolated profile per conversion. See the [full qualification and limitations](../analysis/pierre_lbo_report.md).

The public workbook can be rebuilt from source with `python -m reference.pierre_lbo.workbook build --inputs tasks/pierre_lbo/inputs/base_case.json --output /new/path/pierre_lbo_one.xlsx`, then recalculated. Rebuilding is not a byte-identical substitute for the frozen campaign bundle: use the same frozen files for competing trials.


## Local verification

```bash
"$HOME/.local/share/scraper-bench/runtime/bin/python" -m unittest discover -s tests -v
```

The macOS regressions exercise explicit submission transitions, protected source collection, stdin, scratch writes, private/symlink/runtime-prefix/import/environment/descriptor isolation, fork/subprocess/network denial, execution limits, fresh grading workspaces, strict finite JSON, MCP restart budgets/input integrity, and rejection of forbidden tools/model changes. Real MCP stdio/sandbox smoke evidence supplements the tests. A reference/control run is infrastructure verification, never a candidate-model score.
