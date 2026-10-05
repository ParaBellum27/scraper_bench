# Pierre LBO: holdout generalization and execution-budget analysis

Date: 2026-10-05. Financial task: version 0.2. This analysis interprets the [frozen experiment evidence](../results/pierre_lbo/holdout-controlled-2026-10-05/README.md); it does not revise historical grades or add scenarios to the official scoreboard.

## Decision

**Gemini produced fully correct programs under both matched execution allowances. Twelve executions sufficed in the observed run; 24 did not improve observed accuracy but retained correction headroom.** The original passing program and both new programs also passed a separately qualified, fresh 22-case stress holdout.

This supports a narrow conclusion: the earlier 0/45 runtime failure is not evidence that a 12-execution allowance inherently prevents this model from solving this LBO. It does not establish equal reliability across allowances, identify which earlier workflow change mattered, rank models, or prove general spreadsheet competence.

Keep the current 24-call configuration as the recovery-headroom option; do not describe it as an accuracy improvement demonstrated by this experiment. The 12-call condition is a lower-cost observed success, not a validated reliability-equivalent replacement. No additional trials are authorized or scheduled by this analysis.

## What was tested

The task is replication of an explicitly specified, corrected LBO derivative. It is not an open-ended audit of the author's original workbook and not a financial certification. Outputs include operations, working capital, interest and PIK, maturity obligations, revolver draw/repayment, debt sweeps, retained failure prefixes, exit proceeds, preferred priority and actual-date shareholder returns.

The official evaluation remains **one public base plus 45 changed-input cases**, each with 55 scored fields and relative/absolute numeric tolerances of 1e-7. The primary measure is fully correct cases and the all-pass flags. Weighted partial credit remains diagnostic: the [pretrial integer-year IRR control](pierre_lbo_audit.md#reporting-and-actual-scenario-coverage) scored 97.34/100 while failing 26 hidden cases.

The earlier [oracle audit](pierre_lbo_audit.md) independently qualified all 46 scored cases and nine hand-derived diagnostics using LibreOffice. The new holdout is another **separate** evaluation. Neither its 22 cases nor the nine diagnostics are added to the original hidden denominator.

## Why the holdout adds evidence

The holdout cases were designed without reading the frozen candidate source or its holdout outcomes. Exact inputs and independent arithmetic/branch witnesses were saved before evaluation, and none duplicate the original public/hidden inputs or earlier hand diagnostics. The simple hand setup uses annual EBITDA512, entry equity896 and preferred448.

| Family | Cases | Consumer-visible failure exposed |
|---|---:|---|
| Scaled liquidity neighborhoods | 6 | Absolute funding tolerances or incorrect gross-operand scaling can flip financed/failed status. Shortages are 0.2×/5× the relative guard at scales0.0001×/1×/10000×. |
| Preferred hurdle | 9 | Incorrect priority, ordinary residual or management-return nullness below/equal/above the hurdle; the same relationships are checked at three currency scales. |
| Mandatory term maturity | 2 | Failure to refinance a funded maturity, or continuing financing past an unfunded obligation instead of retaining the earlier prefix. |
| Matured revolver/no redraw | 2 | Reusing unused commitment after maturity, mishandling mandatory repayment, or dropping previously funded financing rows. |
| Fiscal date mechanics | 2 | Resetting a sequentially clamped leap-day anniversary, or stubbing working capital along with one-day operations. |
| Dated returns | 1 | Integer-year annualization rather than actual elapsed days from a leap-day close. |

These are deterministic, partly related stress cases, not 22 independent draws from an economic population. Preferred cases straddle the economic hurdle; they do not exhaust the numerical guard's immediate floating-point neighborhood. Liquidity separations avoid one-ULP serialization ambiguities. The suite does not cover every ownership/tax/maturity combination, extreme representable value, or input distribution.

### Qualification and result

Before reading or executing the supplied frozen program, every new case was built into a workbook and recalculated with **LibreOffice26.8.0.3**. All 55 fields matched the unchanged Python reference at the original grading tolerances. Both implementations additionally passed predeclared independent arithmetic, branch, prefix, date and null-return witnesses. Qualification failure would skip candidate evaluation.

The original passing source then passed **22/22**, without API calls, code edits or model feedback. Its before/after/frozen-copy SHA-256 remained `6966f0c0788aeccbdd55cc9d5c5a21022d1a9669092ea0b0fb25e02b4fb3cd36`. Its historical **45/45** score was not recomputed into a larger denominator.

The independently implemented workbook formulas plus hand witnesses provide more evidence than comparison against the Python oracle alone. They still share the public conventions and cannot establish that those conventions capture every commercial assumption. Native Excel and visual workbook verification remain unavailable.

Evidence: [exact cases](../results/pierre_lbo/holdout-controlled-2026-10-05/holdout/cases.json), [full qualification and frozen-source grades](../results/pierre_lbo/holdout-controlled-2026-10-05/holdout/report.json), [holdout reproduction](../results/pierre_lbo/holdout-controlled-2026-10-05/holdout/README.md).

## Matched execution-allowance comparison

The [preregistered protocol](../results/pierre_lbo/holdout-controlled-2026-10-05/protocol.json) randomized order with host-side seed2026100501: **24-call condition first, 12-call condition second**. This is an order seed, not a provider sampling seed. Both conversations were fresh and received only the same public bundle and logical execution tool, not earlier source, financial failures, hidden results or holdout results.

Only `max_run_calls` changed. Shared conditions were 32 model turns, 1,800 seconds overall, 10 seconds per execution, 65,536 response tokens, identical generic submit-early/reserve-three-calls instruction, native `gemini-3.8-flash`, provider-default temperature/thinking with overrides omitted, and the same task/grader/seed/tolerances. Host labels were provenance only. [Complete effective configuration hashes](../results/pierre_lbo/holdout-controlled-2026-10-05/conditions.json) bound each authorization.

The common cumulative monetary cap remained $4. The later condition had less remaining account allowance, but this did not censor it: both completed, no uncertain Gemini holds remained, and neither was interrupted by the spend guard. Request counts21/13 equal model turns20/12 plus one access probe each; no additional retry requests appear in those counts. Effective sampling defaults and immutable backend revision were not exposed.

### Observed performance

| Measure | 24-call allowance | 12-call allowance |
|---|---:|---:|
| Fully correct original hidden cases | 45/45 | 45/45 |
| Public base | Pass | Pass |
| Fully correct separate holdout | 22/22 | 22/22 |
| All original cases correct | True | True |
| Weighted diagnostic | 100/100 | 100/100 |
| Actual executions | 19 | 12 |
| Model turns | 20 | 12 |
| Provider requests including access probe | 21 | 13 |
| Non-submission inspection errors | 4 | 1 |
| Final explicit submission | Call19, exit0 | Call12, exit0 |
| Unused execution calls | 5 | 0 |
| Stop reason | Normal model stop | Execution allowance exhausted |
| Elapsed runner time | 148.65s | 83.21s |
| Conservative trial cost | $0.77267925 | $0.34812975 |

Both new frozen sources also passed the separate holdout. Thus three frozen programs passed it, but the original was selected because it had already passed the official suite; this is not an unbiased three-run model success-rate sample.

The shorter run cost **$0.42454950 less (54.95%)** and took **65.44 seconds less (44.02%)** in this pair. These are realized contrasts, not expected savings: different stochastic generations used different numbers of inspections, generated different histories and encountered different tool errors. The larger allowance was24, but actual executions were19—not24.

The 24-call run's four errors were inspection-only: missing `openpyxl`, missing `solution_test`, denied subprocess/fork and missing `solution`. The12-call run's inspection error was undefined `res`. All were retained in the evidence; none was a runtime failure of the final graded source. The subprocess denial also shows the execution sandbox remained active.

**The practical distinction is correction margin.** The24-call submission left five calls available. The12-call run used its last call to submit successfully; an error at that point would have left no correction opportunity. The workflow instruction was advisory, not an invariant: neither run explicitly submitted before its final used execution. Passing results do not prove consistent compliance with submit-early advice.

Evidence: [structured outcomes](../results/pierre_lbo/holdout-controlled-2026-10-05/outcome.json), [24-call original grade](../results/pierre_lbo/holdout-controlled-2026-10-05/calls24/original-grade.json), [12-call original grade](../results/pierre_lbo/holdout-controlled-2026-10-05/calls12/original-grade.json), [24-call holdout grade](../results/pierre_lbo/holdout-controlled-2026-10-05/calls24/holdout-grade.json), [12-call holdout grade](../results/pierre_lbo/holdout-controlled-2026-10-05/calls12/holdout-grade.json). Each trial directory preserves metadata, every executed source, execution logs, raw trajectory and immutable final source.

## What the chronology does—and does not—explain

| Attempt | Observed outcome | Valid interpretation |
|---|---|---|
| Initial4096-token response cap | Truncated before explicit submission; ungraded | Protocol/response limitation, not a financial score of zero. |
|8192-token response cap | Truncated before explicit submission; ungraded | Returned `MAX_TOKENS`; exact limiting mechanism remains unexplained despite visible+thinking counts below the requested cap. |
| Standard65536-token condition | Final-call submission raised `NameError` in all46 original cases;0/45 | Executable-delivery failure in that generation, not evidence of45 independent financial reasoning failures. |
| Relaxed condition | Public base and45/45 passed; later22/22 holdout passed | Successful generation after multiple condition changes; causal attribution unavailable. |
| Matched24-call condition | Public base,45/45 and22/22 passed | One successful generation under the larger execution allowance. |
| Matched12-call condition | Public base,45/45 and22/22 passed | One successful generation under the smaller allowance and otherwise identical matched settings. |

The earlier standard/relaxed comparison also changed turns, wall time and the generic workflow. The new matched 12-call success shows that 12 calls do not inherently prevent a correct submission under the matched workflow. It does not rule out the execution limit contributing to the old failure, or establish whether the workflow instruction, extra model turns, wall-time setting or randomness explains the later success. Randomized order and fresh conversations reduce avoidable ordering/carryover problems; one pair cannot measure residual sampling variance or provider drift.

Historical evidence: [initial truncation](../results/pierre_lbo/preparation-2026-10-05/gemini-live-outcome.json), [8192 truncation](../results/pierre_lbo/gemini-only-8192-2026-10-05/outcome.json), [standard runtime failure](../results/pierre_lbo/gemini-only-65536-2026-10-05/outcome.json), [relaxed success](../results/pierre_lbo/gemini-relaxed-2026-10-05/README.md). Do not average adaptive, differently configured attempts into a single reliability estimate.

## Statistical and publication limits

1. **The experimental unit is a fresh model generation.** There is one per allowance, not45 or67 independent model trials. One observed success per condition cannot estimate a reliable difference in success probabilities or establish equivalence.
2. **Cases are deliberately structured.** Related currency variants and common arithmetic make scenario outcomes correlated. Field counts and the number of spreadsheet cells are not statistical sample sizes.
3. **The scoring target is conditional.** This tests specified LBO semantics within the frozen public domain, not arbitrary spreadsheet reconstruction, source-error detection, investment quality or robustness to all valid finite inputs.
4. **Holdout freshness is historical.** Publication discloses these inputs, witnesses, reference code and grading evidence. Future use should call this a disclosed regression/stress suite, not a newly unseen holdout. Generation in this experiment had no access to it.
5. **No cross-provider ranking is supported.** Groq and Mistral's earlier HTTP403/429 access failures yielded no comparable submitted LBO programs. Historical FCFF/CLI outcomes use different tasks/agent conditions and cannot fill those gaps.
6. **Accounting is conservative, not an invoice.** Prompt tokens were costed at full input rates, without inferred cached-input discounts; output includes thinking. Provider billing and unrelated account activity were not independently verified.

## Spending, safety and publication boundary

The two new runs cost **$1.12080900** across34 requests, including access probes. Adding the preserved earlier$1.54151625 gives **$2.66232525 cumulative**, below the unchanged$4 hard cap, with$1.33767475 remaining and zero uncertain Gemini holds. All six claims remain preserved. Both paid access and candidate authorization are closed; publication does not authorize another request.

The branch includes the v0.2 audit/direct-runner prerequisites, new holdout/profile implementations and behavioral tests, this analysis, and immutable result packs. Earlier public evidence stays unchanged. `.env`, the live ignored `runs/` tree, private account confirmations, local runtimes and unrelated working files are not publication targets. Result-pack ledger copies are audit snapshots, not live authorization or a reset mechanism.

Reproduction is offline: use the frozen sources with the unchanged grader, or choose a new directory for actual spreadsheet qualification through `reference.pierre_lbo.holdout`. Real model trials still require fresh explicit authorization, valid pricing/account checks and the persistent spend guard. The [experiment report](../results/pierre_lbo/holdout-controlled-2026-10-05/README.md#evidence-and-verification) records111 passing behavioral tests, successful type checking, real CLI gates,47 frozen source files and exact submission/workbook hashes.
