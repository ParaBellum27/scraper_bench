# Task 001 — Damodaran Two-Stage FCFF Valuation

## Objective

Write a Python program that reproduces the valuation methodology implemented in Aswath Damodaran's `fcff2st` two-stage FCFF model for the supplied benchmark inputs.

The program must calculate the valuation from inputs. Hard-coding the base-case outputs is not permitted.

## Benchmark version 0.1

The first benchmark version freezes the spreadsheet's Yes/No branch settings to the supplied base case and varies numerical assumptions in hidden tests. This isolates whether the model can correctly translate the finance logic into executable software before testing every optional branch in the original spreadsheet.

The active base-case logic is:

- public company with market-value capital weights;
- CAPM cost of equity from beta, risk-free rate and risk premium;
- after-tax cost of debt;
- high-growth rate formed from weighted historical, outside and fundamental growth estimates;
- fundamental growth = return on capital × reinvestment rate;
- capital spending, depreciation and revenues grow with earnings during high growth;
- working capital remains a constant percentage of revenues;
- terminal reinvestment is derived from stable growth / stable return on capital;
- stable-period beta, debt ratio and cost of debt remain unchanged.

## Input

Read `inputs/base_case.json` for the public case. Hidden evaluations will provide the same schema with modified numeric assumptions.

## Required output

Return a JSON object containing at least:

- `fundamental_growth_rate`
- `high_growth_rate`
- `cost_of_equity`
- `equity_weight`
- `after_tax_cost_of_debt`
- `debt_weight`
- `wacc`
- `working_capital_pct_revenues`
- `yearly` — one record per high-growth year with:
  - `year`
  - `ebit_after_tax`
  - `capex_minus_depreciation`
  - `change_working_capital`
  - `fcff`
  - `present_value`
- `terminal_ebit_after_tax`
- `terminal_capex_minus_depreciation`
- `terminal_change_working_capital`
- `terminal_fcff`
- `terminal_value`
- `pv_high_growth_fcff`
- `pv_terminal_value`
- `firm_value`
- `market_value_equity`
- `value_per_share`

Additional fields are allowed.

## Requirements

1. Use Python.
2. Do not use network access.
3. Do not read files outside the task workspace.
4. Do not hard-code the base-case answers.
5. Preserve sufficient numerical precision for evaluator tolerances.
6. Generalize to hidden modifications of numeric inputs, including growth, capital structure, cost of capital, operating assumptions and terminal assumptions.

## Evaluation

Submissions are evaluated on:

- successful execution;
- intermediate financial calculation accuracy;
- yearly FCFF calculation accuracy;
- terminal-period calculation accuracy;
- final enterprise/equity valuation accuracy;
- performance on hidden numerical scenarios;
- resistance to base-case hard-coding.

The benchmark reference implementation and hidden expected outputs are not available to the evaluated model.
