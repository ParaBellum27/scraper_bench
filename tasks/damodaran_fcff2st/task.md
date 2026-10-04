# Task 001 — Damodaran Two-Stage FCFF Valuation

## Objective

Write a single Python program that reproduces the active valuation logic in Aswath Damodaran's `fcff2st` two-stage FCFF model for supplied inputs.

The program must derive the valuation from the inputs. Hard-coding base-case outputs is not permitted.

## Benchmark version 0.1

This version freezes the original workbook's Yes/No switches to the supplied base-case configuration and varies numerical assumptions in hidden tests. This isolates whether a coding model can translate the finance logic into robust executable software before later versions test all optional workbook branches.

Active logic:

- public company with market-value capital weights;
- CAPM cost of equity from beta, risk-free rate and risk premium;
- after-tax cost of debt;
- historical EBIT growth derived from current EBIT and EBIT five years ago;
- fundamental return on capital derived from prior book debt + prior book equity;
- fundamental reinvestment rate derived from net capex + change in working capital;
- fundamental growth = return on capital × reinvestment rate;
- high-growth rate = weighted historical + outside + fundamental growth;
- capex, depreciation and revenue grow at the high-growth rate;
- non-cash working capital remains a constant percentage of revenue;
- terminal reinvestment rate = stable growth / stable return on capital;
- stable-period beta, debt ratio and cost of debt remain unchanged;
- terminal value = next-period FCFF / (stable WACC − stable growth).

## Program interface

Your submission must be one file named `solution.py`.

When executed as:

```bash
python solution.py
```

it must:

1. read exactly one JSON input object from **stdin**;
2. compute the valuation;
3. write exactly one JSON output object to **stdout**.

Do not depend on network access or files outside the task workspace.

## Public input

`inputs/base_case.json` is the public case. Hidden evaluations use the same schema with modified numeric assumptions.

Some supplied fields may be irrelevant under the fixed workbook switches. Your implementation should follow the workbook logic rather than force every input into the valuation.

## Required output fields

Return a JSON object containing at least:

- `cost_of_equity`
- `equity_weight`
- `after_tax_cost_of_debt`
- `debt_weight`
- `wacc`
- `current_fcff`
- `historical_growth_rate`
- `fundamental_roc`
- `fundamental_reinvestment_rate`
- `fundamental_growth_rate`
- `weighted_growth_rate`
- `working_capital_pct_revenue`
- `high_growth_fcff` — numeric list with one element per high-growth year
- `high_growth_pv` — numeric list with one element per high-growth year
- `stable_reinvestment_rate`
- `terminal_fcff`
- `stable_wacc`
- `terminal_value`
- `pv_high_growth_fcff`
- `pv_terminal_value`
- `firm_value`
- `market_value_equity`
- `equity_value_per_share`

Additional fields are allowed.

## Evaluation

The score is based on five calculation blocks:

- discount-rate mechanics — 15%;
- growth and reinvestment mechanics — 15%;
- high-growth FCFF forecast — 25%;
- terminal-value mechanics — 20%;
- enterprise-to-equity valuation bridge — 25%.

The public base case contributes 20% of the final benchmark score. Hidden scenarios contribute 80%.

Hidden evaluation includes targeted changes to discount rates, forecast horizon, growth-source weights, working capital/reinvestment, capital structure, the equity bridge, scale, and an interest-expense invariance check, plus reproducible seeded random cases.

Numerical comparisons use tight floating-point tolerances. A solution that merely hard-codes the public workbook outputs should score poorly on hidden cases.

## Methodological source

Task 001 is grounded in Damodaran's original `fcff2st` workbook and his published FCFF methodology. The benchmark's independent Python reference implementation is used to generate expected outputs for hidden inputs; the original spreadsheet is the base-case numerical oracle used to verify that reference implementation.
