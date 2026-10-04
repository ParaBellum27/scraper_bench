# Coding-task design and evaluation: financial-model replication pilot

**Portfolio evidence for AfterQuery / Mercor** · One independent task · AI-assisted project · Recorded model attempts: 2026-10-04

## What this demonstrates

This AI-assisted pilot measures whether a coding agent can turn a specified financial workbook into a standalone Python program that remains correct when assumptions change. It demonstrates task specification, reference validation, scenario design, and auditable evaluation.

For spreadsheet migration, matching a final valuation is insufficient: incorrect discounting or reinvestment can remain hidden. This task also checks intermediate calculations.

## Task and quality evidence

Source: [Aswath Damodaran's two-stage FCFF workbook](reference/damodaran_fcff2st/SOURCES.md). The candidate receives a task, workbook, and public JSON, then submits one `solution.py`: JSON stdin to JSON stdout, with no workbook available at grading time. The public assumptions should produce approximately **66.78256422 per share**; changing growth assumptions must change the forecast and valuation.

**Implemented and verified:**

- **Reference:** 36 numerical comparisons across 28 outputs matched cached workbook values; maximum absolute difference **2.18 × 10⁻¹¹**. This is base-case reconciliation, not changed-input Excel recalculation.
- **Coverage:** one public case and **13 withheld-during-generation scenarios**—nine targeted, four seeded—belong to **one independent task**, not 14 diverse tasks.
- **Grading:** 23 output fields in five weighted blocks; public case 20%, held-out average 80%; relative tolerance `1e-5`, absolute tolerance `1e-6`. No LLM numerical judge.
- **Hardcoding control:** a constant public answer scored **100 publicly but 44.43 overall**. Both successful model artifacts scored 100 throughout.
- **Execution:** seven regressions passed, exercising private-file/symlink/network denial, time/output limits, fresh grading state, MCP restart/input integrity, and tool/model-change detection. This is bounded evidence, not security certification.
- **Replay:** all three unchanged published submissions reproduced their original per-case grades, including the failure, without new model requests.

## Results—not a leaderboard

Nine persisted finance attempts produced three graded submissions. “—” means **no frozen submission was graded**, not a zero. Runtime is the observed metadata interval, including setup/client overhead.

| Model / condition | Attempts | Accepted Python calls | Score | Held-out ≥95 | Elapsed |
|---|---:|---:|---:|---:|---:|
| Gemini `gemini-3.8-flash`, CLI pilot | 1 | 9 | **100** | 13/13 | ~169s |
| Mistral Medium 3.5 display alias, Vibe pilot | 1 | 12 | **0** | 0/13 | ~223s |
| Same Mistral Vibe selection, separate paired attempt | 1 | 10 | **100** | 13/13 | ~125s |
| Gemini, paired attempt | 1 | 6 | — | — | ~184s |
| Gemini, quota-blocked recovery | 1 | 0 | — | — | ~9s |
| Direct API `mistral-medium-3-5` | 3 | 0 | — | — | ~0.19–0.32s each |
| Mistral browser; underlying model unverified | 1 | 9 | — | — | ~1,164s |

Client versions, authentication and generation settings differ; [exact settings and backend-identity limits](#b-environment-and-grading-contract) are disclosed below. These are model-plus-agent observations, not a controlled model ranking. Measured monetary cost and comparable cross-provider usage are unavailable.

**Lesson:** Mistral's first attempt spent all 12 executions on inspection; its rejected thirteenth call left a workbook-dependent script that scored 0. A separate attempt succeeded. Gemini succeeded once, then hit service/quota failures. Successful tool calls do not guarantee a valid submission. OpenAI inputs were prepared, but no OpenAI result exists.

## Contribution and next production step

**Suggested portfolio description:** “I led an AI-assisted financial-coding evaluation pilot, producing an auditable task contract, numerical-oracle checks, reproducible grading, and explicit failure accounting.”

Project direction and evaluation decisions are evidenced; implementation, execution, and documentation were AI-assisted. The portfolio does not establish sole manual authorship, a novel valuation method, or measured task-production throughput.

**Planned, not completed:** independent changed-input oracle review, more task families, realistic mutation/exploit checks, frozen repeated-run protocols, and cost/review-time measurement. Production gates and evidence gaps follow.

---

# Technical appendix

## A. One end-to-end worked example

This example was executed using the **unchanged Gemini pilot submission**, not the reference posing as a model answer. [Full inputs, actual candidate outputs, and case grades](results/damodaran_fcff2st/pilot-2026-10-04/worked_example.json) are preserved.

1. **Specify the input.** Use the complete [base JSON](tasks/damodaran_fcff2st/inputs/base_case.json). Selected values: EBIT 5186; tax rate 0.2849; capex 2152; depreciation 1228; change in working capital 499; high-growth years 5; stable growth 0.06; stable ROC 0.12. These are an excerpt, not a complete substitute input.
2. **Generate under the task contract.** The historical agent had access to the workbook and public input only, with `run_solution(code)` feedback. Its ninth accepted execution left the final standalone source, SHA-256 `77bbd60ae191b8e49d27990bb1f3190917d729b93291c0188c43d91d45771f91`.
3. **Freeze and execute without the workbook.** The grader copies only that source into a fresh sandbox and supplies the full JSON over stdin.
4. **Compare actual outputs with the reference.** Representative observed values:

   | Quantity | Actual candidate output |
   |---|---:|
   | WACC | 0.09616947555679844 |
   | Current FCFF | 2285.5086000000006 |
   | PV of high-growth FCFF | 12446.561771589957 |
   | PV of terminal value | 56728.59056202631 |
   | Firm value | 69175.15233361626 |
   | Equity value per share | 66.7825642215609 |

   The current-FCFF arithmetic is `5186 × (1 − 0.2849) − (2152 − 1228) − 499 = 2285.5086`. The per-share bridge is `(firm value + 500 − 1822 − 1500) / 993.57`. All required base-case fields received full credit.
5. **Perturb assumptions, not the answer.** The existing `short_high_growth_horizon` case changes years to 3, stable growth to 0.04, and stable ROC to 0.10. In a separate fresh execution, the same candidate produced a three-element forecast and **47.16001005349605 per share**, with case score 100. The complete suite reproduced **100/100, 13/13 held-out cases**.

This demonstrates observed input sensitivity and deterministic replay. It does not independently validate all possible financial inputs.

## B. Environment and grading contract

- **Development:** one public workspace containing task, workbook, and base JSON; one logical MCP tool, `run_solution(code)`, which saves and executes source. Public stdout/stderr only; no held-out grade feedback.
- **Models/settings:** Vibe 2.25.8 selected display alias `mistral-medium-3.5`, configured API alias `mistral-vibe-cli-latest`, account authentication, temperature 1/high thinking; immutable backend revision unknown. Gemini CLI 0.29.5 selected `gemini-3.8-flash`, API-key authentication, CLI generation defaults. Direct Mistral API requested `mistral-medium-3-5`, temperature 0, maximum 8,192 completion tokens/turn; all three attempts failed before a response. The browser's underlying model was unverified.
- **Limits:** native clients configured for 20 turns, 12 accepted executions, 10 seconds/execution, 900 seconds total. Output capture is capped at 64 KiB per stream. Native client turn semantics differ; executions are not provider-request counts.
- **Grading:** five seconds per case; fresh workbook-free directory for every input. Final score is `0.20 × base + 0.80 × mean(hidden)`. Block weights are 15% discount rates, 15% growth/reinvestment, 25% high-growth FCFF, 20% terminal value, 25% equity bridge.
- **Matching:** finite numeric values only; `math.isclose(rel_tol=1e-5, abs_tol=1e-6)`. Arrays must have the expected length and receive element-level partial credit. Missing fields, wrong array types/lengths, and execution/JSON failures lose credit. `hidden_cases_passed_95` is a ≥95 threshold, not a strict-perfect counter.
- **Diversity:** one Damodaran workbook, fixed active switches. Scenario variations exercise discount rates, horizons, growth mixtures, reinvestment/working capital, capital structure, the equity bridge, interest invariance, scale invariance, and four seeded combinations. No demonstrated cross-workbook or cross-domain generalization.
- **Usage:** Gemini's native counters record 293,615 total tokens for the successful pilot and 88,151 for the interrupted pair. Their semantics are client-specific; Vibe lacks comparable usage. No invoice-derived cost is recorded. See the [full run ledger](results/damodaran_fcff2st/pilot-2026-10-04/attempts.json) for exact timestamps/settings and the [audit report](analysis/pilot_report.md) for every diagnostic and failure.

## C. Leakage, grading exploits, and evidence gaps

| Area | Evidence available | Limit / next check |
|---|---|---|
| Private-file and network access | Actual regression attempted out-of-workspace and symlink reads plus a network connection; denied | Directly exercise reference/grader paths and broader native-client escape/prompt-injection attempts; no comprehensive adversarial audit claimed |
| Credentials and process creation | Environment-scrubbing and fork-denial code exist; the regression observed no API-key variables | A seeded credential-canary test and direct fork-denial smoke are not recorded in this evidence pack; do not treat their effectiveness as independently demonstrated |
| State/budget manipulation | Actual MCP restart tests preserved spent budget and original stdin after candidate modified the public input file | Broader concurrency/resource-abuse coverage remains unmeasured |
| Forbidden tools/model switching | Tests verify audit rejection of a synthetic shell event and per-turn model-change record | Post-event audit tests do not prove every client version prevents every unauthorized action before it occurs |
| Hardcoded answer | Constant base-output control falls to 44.43 overall; only 1/13 held-out cases reaches 95 | It legitimately passes interest invariance and earns partial credit on unchanged fields; realistic wrong-formula mutants and targeted grader exploitation remain to be tested |
| Oracle validity | Cached base-case values reconciled; cell-level evidence published | Next: independently recalculate changed-input cases and obtain financial review; avoid validating every oracle against itself |
| Holdout secrecy/contamination | Agent workspaces excluded held-out inputs/reference; candidate-boundary regressions passed | Released cases are now public. Training contamination was not assessed; use a new reviewed holdout for future selection |
| Reproducibility | Exact frozen sources and all historical per-case scores replayed | Workbook redistribution permission is undocumented; workbook omitted. Backend revisions and immutable per-run harness builds are not fully pinned |
| Comparative inference | All nine attempts retained; six have no score | More independent tasks and fresh-state repetitions under frozen conditions are needed; 13 scenarios are not 13 independent model samples |

The configured macOS sandbox is not a claim of a fully isolated provider client, portable container, or comprehensive security boundary. Claims above are limited to the actions actually exercised.

## D. Practical process for producing more verified tasks

**Proposed production workflow; throughput not yet measured:**

1. Select a source with documented provenance and permitted use. Define an independently meaningful task, supported branches, units, I/O schema, and clear success criteria.
2. Build a traceable reference and reconcile it with an independent source/engine on both base and changed inputs. Have another reviewer check financial conventions and specification clarity.
3. Design tests from requirements and plausible mistakes; include valid boundaries, invariants, multiple interacting changes, correct alternative implementations, and intentionally wrong formula variants. Keep development and evaluation material separate.
4. Exercise candidate access, state, budget, parser and grading-abuse boundaries with explicit expected outcomes. Record what remains untested.
5. Freeze the source/runtime/test versions, sampling settings and recovery policy. Run a balanced, fresh-state campaign; preserve every attempt and separate service failures from scored submissions.
6. Review failures against code/trajectory evidence, publish sanitized replay artifacts, and measure task-authoring/review time plus comparable run cost before claiming production capacity.

This process follows the principles researched in [HELM, HumanEval, EvalPlus, SWE-bench Verified, and Inspect](analysis/benchmark_design.md): explicit scope, executable correctness, strong reviewed tests, controlled conditions, and transparent failure accounting. These are methodological references, not endorsements of this pilot.

## E. Reproduce the historical scores

Use the supported macOS runtime and dependency setup in the [evidence-pack instructions](results/damodaran_fcff2st/pilot-2026-10-04/README.md). From the repository root:

```bash
PYTHON="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PYTHON" -m evaluator.run_grader \
  results/damodaran_fcff2st/pilot-2026-10-04/submissions/gemini-cli-pilot-01.py \
  --seed 20261003 --timeout 5 --summary-only
```

Expected recorded summary: score 100; public 100; held-out average 100; 13/13 cases at ≥95. The other two published files reproduce 0 and 100 respectively. No model credentials or workbook are required for this offline replay. A successful grader exit alone does not imply candidate success—inspect its score.

**Evidence index:** [frozen submissions and sanitized results](results/damodaran_fcff2st/pilot-2026-10-04/README.md) · [actual verification output](results/damodaran_fcff2st/pilot-2026-10-04/verification.json) · [complete technical report](analysis/pilot_report.md) · [benchmark-design research](analysis/benchmark_design.md).
