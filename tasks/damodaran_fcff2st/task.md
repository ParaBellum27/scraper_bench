# Task 001 — Damodaran Two-Stage FCFF Valuation

## Objective

Write a Python program that reproduces the valuation methodology implemented in Aswath Damodaran's `fcff2st.xls` workbook.

Your program must compute the valuation from the supplied inputs rather than hard-code any workbook outputs.

## Requirements

1. Read the benchmark inputs supplied with the task.
2. Implement the financial logic represented in the source workbook.
3. Produce outputs using the benchmark's required schema.
4. Preserve sufficient numerical precision for evaluator tolerances.
5. Generalize to modified assumptions used in hidden tests.
6. Do not depend on network access.
7. Do not read files outside the task workspace.

## Evaluation

Submissions will be evaluated on:

- successful execution;
- base-case numerical correctness;
- correctness of intermediate calculations;
- final valuation correctness;
- robustness under hidden assumption changes;
- absence of hard-coded base-case answers.

The exact input and output schemas will be finalized after the source workbook is inspected and the reference implementation is verified.
