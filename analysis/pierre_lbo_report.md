# Pierre LBO One — qualification and next trial protocol

## Decision and status

A separate `pierre-lbo` branch prepares the author's LBO as a second benchmark task. It evaluates replication of a **specified, corrected derivative**, not replication of faulty original caches and not an open-ended repair exercise.

The public bundle is frozen at `tasks/pierre_lbo/`: `task.md`, `pierre_lbo_one.xlsx`, and `inputs/base_case.json`. An identical local campaign copy is under ignored `runs/private/pierre_lbo/frozen-public/`. The original remains outside Git and unchanged; its audit and source-to-input mapping are in [SOURCES.md](../reference/pierre_lbo/SOURCES.md).

**Readiness:** independently recalculated spreadsheet and Python outputs match across **46/46 scenarios, all 55 output fields**, with relative and absolute numeric tolerances of 1e-7. Calculation engine: **LibreOffice 26.8.0.3**, not native Excel. All 29 local regressions passed; type checking passed across `harness`, `evaluator`, `reference`, and `tests`. Real MCP stdio loaded the public workbook and executed the standalone reference through the sandbox. No new candidate-model requests have been made.

## Why this task adds useful coverage

FCFF has 23 scored outputs. Pierre LBO has 55, including actual-date timing, annual operating drivers, working-capital movements, two debt balances, cash interest and PIK, taxes, mandatory principal, revolver borrowing/repayment, cash sweeps, an exit bridge, preferred priority, and shareholder returns.

The 45 changed-input cases cover the other three original profiles, individual assumption shocks, interacting financing shocks, revolver draw/repayment priority, early maturity and refinancing, first/later liquidity shortfalls, capped amortization and sweeps, preferred-hurdle boundaries, zero-investment investors, underwater/loss-making exits, short stubs, leap dates, scaling, and four seeded operating/financing mixes. The public profile is not duplicated as a hidden case.

These are **scenarios within one LBO task**, not 45 independent tasks. Greater financial coverage does not prove that current models will fail. Actual model difficulty remains unmeasured until candidate trials run.

## Financial choices frozen before model runs

The user chose to correct the source before replication, keep **1 December** fiscal year-end, and derive cash flow from operating drivers instead of retaining the independent FCF-margin forecast.

The public specification additionally makes implementation conventions explicit: period 1 is the first post-close fiscal end; entry/exit multiples use annual EBITDA; stub operating fractions differ from ACT/365 interest fractions; working-capital changes are not stubbed; interest uses opening debt; tax excludes PIK deductions and loss carryforwards; revolver repayment precedes TLB sweep; maturities are fiscal-period buckets; preferred belongs to the sponsor; there are no interim dividends; specified zero-investment/zero-proceeds returns are null.

Source errors include an EBITDA-margin date denominator, free cash flow being used as a working-capital movement, inconsistent enterprise/equity distributions, static debt, blank exit-fee/preferred mechanics, stale sensitivity caches, and exit-index/range inconsistencies. Original headline outputs are therefore not this task's expected answers.

### Qualified base-case values

Amounts are GBP thousands; differences in the last displayed digit can reflect spreadsheet serialization.

| Output | Corrected value |
|---|---:|
| Exit date | 2026-12-01 |
| Holding period, ACT/365 years | 4.8328767123 |
| Entry EBITDA | 13,802 |
| Entry enterprise value | 110,416 |
| Entry equity | 50,416 |
| Exit annual EBITDA | 39,869 |
| Exit enterprise value | 318,952 |
| Exit fees | 9,568.56 |
| Exit debt | 60,000 |
| Exit cash | 70,227.299315 |
| Equity proceeds | 319,610.739315 |
| Preferred payout | 65,817.864130 |
| Deal MoM / IRR | 6.339470× / 46.540502% |
| Sponsor MoM / IRR | 5.895023× / 44.353014% |
| Management MoM / IRR | 50.339748× / 124.984601% |

These values follow the documented derivative conventions. They are not an independent investment recommendation or a financial certification of the original transaction.

## Qualification found an actual oracle defect

The first spreadsheet reconciliation passed 45/46 cases. At the preferred hurdle, Python calculated exit EV as `233.00000000000003`, leaving a management payout of approximately `5.68e-15`; Calc calculated the intended zero residual. Python returned management IRR approximately −100%, while the spreadsheet returned null. Numeric tolerance alone cannot reconcile a number with null.

The fix is a **general, scale-relative preferred-hurdle rounding rule**, not removal or special-casing of that scenario: if equity proceeds less preferred accrual are at most `1e-12 * equity_proceeds`, all proceeds go to preferred and ordinary proceeds are zero. Otherwise the preferred accrual is paid and the positive residual goes to ordinary. Total distributions are conserved. The rule is included in the public task and both implementations. A regression failed before the fix and passed afterward. Recalculation then passed all 46 cases.

Initial failed qualification evidence remains local under `runs/private/pierre_lbo/qualification-calc/`; final evidence is [qualification.json](../results/pierre_lbo/qualification-2026-10-04/qualification.json). No candidate has been scored against the defective oracle.

## Deliberate-error controls expose the limits of partial credit

These are synthetic validation programs, **not model submissions**. Each ran through the actual isolated grader over the public base plus all 45 changed-input cases.

| Control | Overall score | Base score | Fully correct hidden cases |
|---|---:|---:|---:|
| Standalone reference | 100.00 | 100.00 | 45/45 |
| Constant public-base output | 44.76 | 100.00 | 0/45 |
| Ignore cash interest | 78.36 | 69.51 | 16/45 |
| Ignore cash sweep | 96.11 | 100.00 | 37/45 |
| Ignore preferred priority | 90.86 | 89.09 | 8/45 |
| Use integer years for IRR | 97.34 | 95.91 | 19/45 |

The integer-year IRR control scored at least 95 in **every** hidden case while producing incorrect outputs in 26. The cash-sweep control matched the zero-sweep base case but failed eight changed-input cases.

The grader now reports `base_case_fully_correct` and `hidden_cases_fully_correct` separately from the existing partial-credit score and `hidden_cases_passed_95`. “Fully correct” means every required field matches within its specified tolerance, with no missing fields or execution error. It does not mean mathematically exact binary equality. Scoring weights were not manipulated to force larger penalties after observing these controls. Future analysis must show incorrect field groups and fully correct cases, not treat a 95-point threshold as financial correctness.

Control summaries are in [controls.json](../results/pierre_lbo/qualification-2026-10-04/controls.json). The exact synthetic scripts and per-case grades are retained locally under `runs/private/pierre_lbo/controls-qualified/`.

## Harness and historical regression evidence

- The graders share scalar/array comparison logic, but each task selects its own reference, cases, score groups, seed and tolerances through `--benchmark`.
- Terminal/API runners accept `--workbook-name`, so the candidate sees `pierre_lbo_one.xlsx` rather than a misleading FCFF filename. MCP describes the task-specified workbook.
- A real MCP stdio smoke exposed only `run_solution`, read all five public workbook sheets, and executed the reference on public stdin in two allowed calls. The resulting 55 fields matched the independent spreadsheet. Provider requests: zero.
- The FCFF default system prompt still matches the frozen historical prefix. Replaying all three frozen FCFF submissions reproduced their score/case-count metrics: 100 with 13/13, 0 with 0/13, and 100 with 13/13 at the historical 95-point threshold.
- Historical evidence-pack hashes describe their recorded source snapshot, not this branch's later shared-harness changes. Historical submissions and grades were not rewritten.

## Calculation-engine and visual limitations

Microsoft Excel 16.113.3 answered a version query, but opening the derivative timed out with AppleEvent error −1712; a later workbook-state query also timed out. System Events inspection timed out and screen capture was unavailable. No existing workbook was closed or saved, and no application-wide calculation or alert setting was changed. A specific permission or modal-dialog cause was not observed.

Qualification used LibreOffice's real formula engine and native XIRR instead. LibreOffice was installed only in the benchmark's private user-tools directory, not `/Applications`; each conversion used an isolated temporary profile. Its [official Apple Silicon download](https://download.documentfoundation.org/libreoffice/stable/26.8.0/mac/aarch64/LibreOffice_26.8.0_MacOS_aarch64.dmg.mirrorlist) was verified against SHA-256 `8858d8058da4f862f47559486814e65efc27294da67c5e4bb56b006b1ee59f89`. The [documented headless conversion interface](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html) was used.

This is **independent spreadsheet-engine qualification**, not a claim of native Excel or visual-formatting verification. The native Excel qualification option remains available when interactive automation is accessible. Neither implementation agreement nor regression tests validate unstated commercial assumptions.

## Next model-test procedure

1. Use the frozen three-file public bundle without editing assumptions or instructions between competitors. Artifact hashes are in the task metadata and evidence manifest.
2. Start with one prespecified trial per target under the existing 20-turn, 12-execution, 10-second execution and 900-second wall limits. Preserve actual client/model/authentication/generation settings; these are model-plus-agent trials, not a controlled model-only comparison.
3. Keep hidden cases, reference code, and all grading feedback outside the generation workspace. Freeze the last submitted program before grading. Never repair a candidate manually or return hidden failures to that attempt.
4. Grade with `--benchmark pierre_lbo`; report weighted score, fully correct cases, incorrect groups, execution failures, tool usage, elapsed time, and available token/cost data.
5. Distinguish source-model defects, financial-logic errors, implementation errors, and harness/provider failures. A provider failure without a frozen candidate is ungraded, not a model score of zero.
6. Gemini's last recorded API condition exhausted its daily quota and requested a retry around **2026-10-05T00:00:00Z**. That reset has not been rechecked. Do not silently substitute an account/client/model or compare an unpaired Mistral run as a controlled paired result.
7. Once both targets are available, repeat paired trials before drawing comparative conclusions. Treat these repository-disclosed scenarios as development/regression material; reserve fresh scenario families for later validation rather than tuning prompts on the same revealed failures.

See [harness commands](../harness/README.md#pierre-lbo-one) and the [public task](../tasks/pierre_lbo/task.md).
