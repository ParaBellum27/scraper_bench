# Pierre LBO One pretrial audit — 2026-10-05

## Decision

The financial benchmark is audited and frozen as **version 0.2**. Candidate trials remain unauthorized and blocked on the execution prerequisites below. No provider/access-check requests, paid API calls, candidate trials, browser tabs, or original-workbook modifications occurred during this audit. Reference/control executions are infrastructure verification, not model results.

## Confirmed issues and fixes

| Area | Confirmed issue | Fix and evidence |
|---|---|---|
| Public contract | Wording described capex as positive while zero capex is valid; finite inputs alone allowed unrepresentable compounding/calendar arithmetic. | Clarified nonnegative expenditure, mutually supported Gregorian dates and finite representable intermediates/non-null outputs. All 55 public fields equal the scored fields; all 45 actual hidden inputs remain in scope. No new finance feature or hidden scoring case was added. |
| Liquidity boundary | The absolute `1e-8` shortage guard classified the same economic deficit differently after currency scaling. A `5e-9` shortage scaled by 0.001, 1 and 1000 was previously financed, financed, failed. | Public task, Python and independent spreadsheet now use `1e-12` times the largest gross row cash-flow/obligation/capacity operand, without an absolute floor. All three scaled deficits fail consistently. Gross operands cover EBITDA/capex cancellation. |
| Qualification | Extraction could manufacture null exit values on failed financing, ignore executed caches beyond the funded prefix, and hide a nonblank failure-period cache on a financed exit. | Read/validate the actual caches and reject all three inconsistencies. Qualification enforces 46 distinct scored cases, exactly 55 distinct scored fields, nonempty hand diagnostics, valid expected subsets and globally unique workbook names. |
| Submission | Every inspection overwrote `solution.py`; collecting that writable file could submit an inspection or candidate-mutated program. | `run_solution(code, submit=False)` is inspection by default. Only explicit `submit=True` selects the exact source, captured privately before execution even if execution errors. Later inspection/workspace writes cannot change it. Hash-validated host snapshots are the only finalization source. Missing explicit submission is ungraded. API, terminal, MCP and public prompts use the same contract. |
| Isolation | Entire Python prefixes were readable; synthetic credentials there leaked. A private run directory inside an allowed package could expose snapshots, and arbitrary stdlib siblings were implicitly allowed. | Limit runtime grants to interpreter-declared components, required packages/libraries and specific resources; explicitly deny the repository. Reject public/private runtime overlap. Real canaries reproduced leaks before repair and denial afterward. Clean environment, closed inherited descriptors, network/fork/subprocess denial and fresh evaluation workspaces remain enforced. |
| JSON/reporting | Python's default JSON decoder admitted NaN/Infinity, including unscored fields. High weighted scores could be mistaken for full financial passes. | Reject nonfinite JSON, including numeric overflow such as `1e999`. Primary result is fully correct hidden scenarios out of 45; explicit `all_hidden_cases_correct` and `all_cases_correct`. Weighted score remains diagnostic; current reports remove the 95-point pass count. |
| Generation settings | Existing direct Mistral adapter forced temperature zero, contrary to the requested provider default. | Omit the override and record requested default without inventing an effective backend temperature. No inference was used to test it. |

The preferred-hurdle guard remains relative `1e-12`; grading remains relative/absolute `1e-7`. Tests straddle the liquidity guard (including adjacent binary64 values) and preferred guard across three currency scales. Ordinary numeric roundoff remains tolerated; exact status, failure prefix, dates and null-versus-number semantics are not replaced by broad financial forgiveness. No demonstrated valid implementation rejection justified widening grader tolerances.

## Independent reference verification

Historical evidence was inspected against **all 46 actual calculated XLSX files**, not just its summary: hashes, input scenarios, extracted caches and 55-field schemas matched the records. Fresh qualification then rebuilt and recalculated every case using **LibreOffice 26.8.0.3**, with an isolated profile per conversion.

- Scored cases: **46/46**, public base plus the unchanged 45 hidden scenarios.
- Independent arithmetic diagnostics: **9/9**, separately reported, not extra scoring cases.
- Every workbook: **55 fields** compared between Python and spreadsheet.
- Diagnostic expected subsets are additionally checked against both implementations, not generated from the oracle.

Hand-derived examples in [HAND_EXAMPLES.md](../reference/pierre_lbo/HAND_EXAMPLES.md):

- Debt priority: first revolver draw `D=100*365/366`; next-year interest `D/10`; repay revolver `D`, sweep term principal 100, retain cash `366-1.1*D-100`.
- Liquidity failure: period-two deficit `500-366=134`, capacity 10, shortage **124**; retain one financing row and all three planned forecast periods.
- Preferred waterfall: proceeds **132/133/134**, preferred claim **133**, preferred distributions **132/133/133**, ordinary **0/0/1**, management **0/0/0.2**.
- Dated returns: 276-day hold, proceeds **632**, investment **266**, IRR `(632/266)^(365/276)-1`.
- Three currency scales of a small genuine funding shortfall.

## Reporting and actual scenario coverage

[scenario-feature-map.json](../results/pierre_lbo/audit-2026-10-05/scenario-feature-map.json) records each case's changed inputs and output/period witnesses. Planned timing/operating arrays are distinguished from executed financing rows. For example, `term_maturity` actually fails in period two after only one funded row: it tests a maturity funding failure, not a successful maturity repayment. Separate refinancing and funded-revolver-maturity scenarios exercise successful repayments.

Fresh deliberately flawed controls, rebuilt from the current reference and executed through the real isolated grader:

| Control | Fully correct hidden | All 45 pass? | Weighted diagnostic |
|---|---:|---|---:|
| Reference | 45/45 | Yes | 100.00 |
| Constant public answers | 0/45 | No | 44.76 |
| Ignore cash interest | 16/45 | No | 78.36 |
| Ignore cash sweep | 37/45 | No | 96.11 |
| Ignore preferred priority | 8/45 | No | 90.86 |
| Integer-year IRR | 19/45 | No | 97.34 |

## Exercised verification

- **54/54** behavioral tests passed; **8/8** executor regressions passed again after final fail-closed runtime discovery guards.
- `ty check` passed for `harness evaluator reference tests`; retained workbook-smoke reproducer also type-checked.
- Parent independently replayed real MCP stdio, explicit submission/inspection/mutation transitions, private/symlink/runtime/.env/import denial, environment stripping, descriptor closure, fork/subprocess/network denial and evaluation isolation.
- Final public workbook loaded through MCP; three accepted calls exhausted the smoke budget while preserving call-two submission. Its isolated evaluation matched all 55 independently recalculated spreadsheet outputs.
- All three frozen historical FCFF submissions retained their prior scores and every per-case score: **100, 0, 100**. Historical artifacts were not rewritten.

## Freeze and reproduction

[metadata.json](../tasks/pierre_lbo/metadata.json) identifies public version 0.2; [artifact_manifest.json](../results/pierre_lbo/audit-2026-10-05/artifact_manifest.json) records exact public, source, evidence and runtime versions. The original version 0.1 evidence and private frozen bundle are retained; the new private public-only copy is `runs/private/pierre_lbo/frozen-public-v0.2/`.

From the repository root, using new output directories:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
SOFFICE="$HOME/.local/share/scraper-bench/tools/LibreOffice-26.8.0.app/Contents/MacOS/soffice"
"$PY" -m reference.pierre_lbo.qualify --engine libreoffice --soffice "$SOFFICE" \
  --output-dir runs/private/pierre_lbo/requalification
"$PY" -m reference.pierre_lbo.controls --output-dir runs/private/pierre_lbo/recontrols
"$PY" results/pierre_lbo/audit-2026-10-05/mcp-workbook-smoke.py
```

## Remaining blockers and limits

The [trial plan](../results/pierre_lbo/audit-2026-10-05/trial-plan.json) records the exact requested targets: Groq `openai/gpt-oss-120b`, Gemini `gemini-3.8-flash`, Mistral `mistral-medium-latest`; direct API, one exploratory trial each, concurrency one, provider-default temperature/thinking. Shared requested budgets are 20 turns, 12 executions, 10 seconds per execution, 900 seconds per trial including waits; grading uses 5 seconds per case. Groq is free-only; Gemini has a cumulative $2 cap including checks/retries; Mistral is remaining-included-only, at most $10 with no additional cash spend.

Before candidate execution:

1. Obtain user approval and verify the updated Gemini key belongs to Default Gemini Project before applying its supplied Tier 1 quotas.
2. Implement/verify the missing Groq and Gemini direct adapters, authoritative updated `.env` loading, common direct-API wall deadline, rate pacing and bounded retries. Existing CLI adapters are not substitutes.
3. Enforce persistent cumulative spend/remaining-allowance guards with worst-case next-request reservation, including access checks/retries. Current monetary caps are requirements, not implemented enforcement.
4. Freeze output-token caps and pricing in that execution layer and complete separate provider/quota/truncation reporting. Current Mistral cap is 8192 and per-request timeout is 180 seconds; a common direct-API wall cap is not yet enforced. Effective provider defaults and resolved `latest` version are not known without provider evidence and are not invented in the freeze.

Native Excel and visual spreadsheet-format verification remain unperformed; the actual calculation proof is LibreOffice. The fixed cases do not exhaust every valid input or establish universal numerical correctness. Installed interpreter/allowed package/system-library contents are trusted, not credential storage; a compromised host/runtime is outside the sandbox threat model. The scenarios are repository-disclosed regression material, not a fresh secret holdout. No model-quality conclusion follows from these infrastructure checks.
