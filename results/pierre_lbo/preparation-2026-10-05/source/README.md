# Finance Coding Benchmark

A benchmark for evaluating whether coding-capable language models can translate real financial-modeling logic into correct, executable, and robust Python programs.

## Benchmark results

- [FCFF benchmark summary](BENCHMARK_SUMMARY.md)
- [Complete pilot report](analysis/pilot_report.md) — methodology, every recorded attempt, diagnostics, and conclusions.
- [Model comparison](analysis/model_comparison.md) — where Gemini or Mistral did better in the observed runs, and why the evidence does not establish an overall winner.
- [Research-backed benchmark assessment](analysis/benchmark_design.md) — design principles, evidence gaps, and proposed next steps.
- [Reproducible evidence pack](results/damodaran_fcff2st/pilot-2026-10-04/README.md) — frozen submissions, per-case grades, CSV/JSON ledger, hashes, and offline commands.
- [Pierre LBO One qualification](analysis/pierre_lbo_report.md) — corrected source model, independent spreadsheet reconciliation, and deliberate-error controls; no candidate-model runs yet.
- [Pierre LBO pretrial audit](analysis/pierre_lbo_audit.md) — version 0.2 contract, explicit submission, tightened isolation, 46-case qualification plus nine hand-derived diagnostics, strict correctness reporting, and remaining execution gates.

The recorded campaign contains **nine finance attempts: three graded submissions scoring 100, 0, and 100; six attempts without a graded submission**. This is one independent workbook task, not a model leaderboard. All three frozen submissions reproduced their historical grades; seven local regressions and the harness/test type check passed. See the evidence pack for actual outputs and limitations.

**Observed comparison:** Gemini performed better in the initial native pilot (100 versus 0). Both models later had a 100/100 submission; Mistral's successful run had lower elapsed time, while Gemini's used one fewer Python execution. Mistral completed the concurrent paired attempt, while Gemini was interrupted by service/quota failures. These are different advantages under different conditions, not a controlled model ranking.

## Current scope

Task 001 reproduces Aswath Damodaran's two-stage FCFF valuation spreadsheet (`fcff2st.xls`) in Python.

Task 002, **Pierre LBO One**, reproduces a corrected author-supplied LBO. Its 55 outputs cover operating forecasts, dated cash flows, debt and liquidity, an exit bridge, and preferred/common shareholder returns. The [public bundle](tasks/pierre_lbo/) includes the recalculated derivative workbook; the original stays private. Independent Calc/Python qualification passed 46/46 scenarios. Native Excel automation was unavailable, so this is not a claim of native Excel verification.

The benchmark tests more than whether a model can match one final valuation. A strong submission must:

1. derive the workbook's intermediate calculations correctly;
2. forecast cash flows across the requested horizon;
3. implement the task's financing, terminal-value, and exit-distribution rules;
4. remain correct when assumptions change in hidden tests;
5. avoid hard-coding public outputs;
6. execute as a one-file program under a constrained runner.

## Repository structure

```text
.
├── README.md
├── tasks/
│   ├── damodaran_fcff2st/
│   │   ├── task.md
│   │   ├── metadata.json
│   │   └── inputs/base_case.json
│   └── pierre_lbo/
│       ├── task.md
│       ├── metadata.json
│       ├── pierre_lbo_one.xlsx
│       └── inputs/base_case.json
├── evaluator/
│   ├── grader.py
│   ├── hidden_cases.py
│   ├── benchmarks.py
│   ├── pierre_lbo_cases.py
│   ├── run_grader.py
│   └── schemas.py
├── reference/
│   ├── damodaran_fcff2st/
│   │   ├── reference.py
│   │   ├── expected_outputs.json
│   │   └── SOURCES.md
│   └── pierre_lbo/
│       ├── reference.py
│       ├── workbook.py
│       ├── qualify.py
│       └── SOURCES.md
├── harness/
├── tests/
├── requirements.txt
├── BENCHMARK_SUMMARY.md
├── results/
│   ├── damodaran_fcff2st/pilot-2026-10-04/
│   └── pierre_lbo/qualification-2026-10-04/
└── analysis/
    ├── pilot_report.md
    ├── model_comparison.md
    ├── benchmark_design.md
    ├── pierre_lbo_report.md
    └── failure_taxonomy.md
```

## Task 001: Damodaran FCFF two-stage valuation

The candidate writes one `solution.py` file. For each evaluation case, the runner sends one JSON input object over stdin and expects one JSON output object on stdout.

The public base case reproduces the supplied `fcff2st.xlsx` workbook. The independent Python reference implementation matches the workbook's base-case calculations to floating-point precision.

### Scoring

Each case is scored across five blocks:

- discount rate mechanics — 15%;
- growth and reinvestment — 15%;
- high-growth FCFF forecast — 25%;
- terminal value — 20%;
- enterprise-to-equity bridge — 25%.

The public base case contributes 20% of the overall score and hidden scenarios contribute 80%.

### Hidden evaluation

The current suite contains 13 hidden scenarios:

- targeted discount-rate stress;
- short and long high-growth horizons;
- mixed historical / outside / fundamental growth weights;
- reinvestment and working-capital changes;
- capital-structure changes;
- equity-bridge changes;
- interest-expense invariance;
- scale invariance;
- four deterministic seeded random cases.

The random cases use a benchmark seed for deterministic reproduction. The disclosed v0.1 cases are now public regression material, not a fresh secret holdout for future model or prompt selection.

## Task 001 ground truth

The benchmark is based on Damodaran's own methodology rather than a generic DCF approximation:

- the supplied `fcff2st.xlsx` workbook is the base-case numerical oracle;
- `reference.py` independently reproduces the active spreadsheet formulas;
- Damodaran's Stern valuation materials are used to cross-check the growth, reinvestment and terminal-value relationships;
- held-out expected outputs are generated by the base-case-reconciled reference implementation; independent changed-input workbook recalculation remains a documented gap.

See `reference/damodaran_fcff2st/SOURCES.md` for source links.

## Task 002: Pierre LBO One

The author chose a corrected derivative, 1 December fiscal year-end, and cash flow reconciled to operating drivers. The new task freezes explicit debt, tax, timing and waterfall conventions before model runs. See the [source audit](reference/pierre_lbo/SOURCES.md) and [public specification](tasks/pierre_lbo/task.md).

It has 45 changed-input scenarios in addition to the public base. Each case weights timing/status 5%, funding 10%, operations 25%, debt/cash 30%, exit bridge 15%, and waterfall/returns 15%; base and hidden weights remain 20%/80%. Numeric tolerances are 1e-7 relative and absolute.

**Fully correct hidden cases are the primary measure:** report the count out of 45 and `all_hidden_cases_correct`; `all_cases_correct` additionally requires the public base to pass. The weighted `score` is a partial-credit diagnostic only. A deliberate integer-year IRR bug scored 97.34/100 while failing 26 scenarios. Current reports remove the misleading 95-point pass count and attach actual financial-feature witnesses to every case.

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PY" -m evaluator.run_grader reference/pierre_lbo/reference.py \
  --benchmark pierre_lbo --summary-only
```

The version 0.2 reference control scored 100 with all 45 hidden cases fully correct. Independent LibreOffice 26.8.0.3 recalculation passed all 46 scored scenarios and nine separate hand-derived diagnostics, comparing all 55 fields per workbook. The audit repaired currency-dependent liquidity classification, qualification cache blind spots, implicit submission overwrites, and overbroad runtime access. The original workbook remains untouched; native Excel verification remains unavailable. See the [pretrial audit](analysis/pierre_lbo_audit.md).

The [guarded direct campaign](harness/README.md#guarded-direct-api-campaign) now implements Groq, native Gemini and Mistral adapters, current-key loading, deadlines, rate/retry controls and persistent spend reservations. The [executable policy](harness/direct_policy.json) fixes model IDs, 4,096-token output caps, pricing and quotas. Access checks and candidate trials have separate private release gates; preparation evidence is retained in [results](results/pierre_lbo/preparation-2026-10-05/). No Pierre candidate trials have started. The earlier audit trial plan remains historical. Final source requires `run_solution(code, submit=True)`; inspection cannot replace it.

## Historical FCFF targets and observed conditions

- OpenAI/Luna label — unrun; actual model identity and access still need verification.
- Mistral Medium 3.5 — completed Vibe attempts; direct API attempts were quota-blocked.
- Gemini 3.8 Flash — one completed CLI attempt plus interrupted paired/recovery attempts.

The current direct campaign and historical terminal runners share the macOS Python sandbox; see [harness/README.md](harness/README.md). Terminal results are model-plus-agent pilots, not interchangeable with the guarded direct-API condition. Available model labels alone do not establish inference entitlement.

## Task 001 validation status

- [x] Repository architecture defined
- [x] Source workbook inspected
- [x] Workbook formulas and dependencies mapped
- [x] Independent Python reference implementation built
- [x] Base case matched to workbook outputs
- [x] Input/output schema frozen for v0.1
- [x] Weighted grader implemented
- [x] Targeted hidden tests implemented
- [x] Seeded random hidden tests implemented
- [x] Subprocess runner implemented
- [x] Correct reference solution scores 100/100 locally
- [x] Hard-coded base-case solution is strongly penalized by hidden tests
- [x] Add Mistral API runner with public-only tool feedback and saved trajectories
- [x] Sandbox development and per-case grading without network or hidden-file access
- [x] Add official Mistral/Gemini terminal runners with a public-only MCP execution tool
- [x] Run and independently grade initial Gemini CLI and Mistral Vibe pilots
- [ ] Run the OpenAI/Luna target after verifying its actual model identity and access
- [x] Record initial terminal-pilot failure analysis in `analysis/failure_taxonomy.md`
- [ ] Collect repeated trials before drawing comparative conclusions
