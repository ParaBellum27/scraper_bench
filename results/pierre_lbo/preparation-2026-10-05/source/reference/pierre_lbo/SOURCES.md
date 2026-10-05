# Pierre LBO One: source audit and modeling decisions

## Provenance and privacy

The author supplied `Pierre Duke LBO copy.xlsx`. Its frozen original has SHA-256:

```text
7958823b280bdb326998f06884a6feb73cf6e7301a4f9410b10133689075397a
```

The original and byte-identical frozen copy are not modified or committed. Local evidence is under ignored `runs/private/pierre_lbo/`: `source/pierre_lbo.xlsx` and `workbook_inventory.json`. The inventory records formulas, cached values, formats, defined names, external links, and calculation settings.

The source contains five sheets (`LBO`, `Returns`, `Values`, `Assumtions`, `Organic`), 1,013 formula cells, and 1,512 nonempty cells. Formula counts include two data-table formulas. No missing formula caches or explicit cached error cells were observed. This does **not** establish financial correctness.

## Findings that prevent treating cached outputs as ground truth

| Source location | Observed issue | Corrected derivative treatment |
|---|---|---|
| `Values!I18` | EBITDA margin divides EBITDA by `I8`, an Excel date serial, rather than revenue. The cached result is approximately 30.7422%; 13,802 / 158,324 is approximately 8.7176%. | EBITDA margin is gross-profit margin minus opex margin, consistent with the operating forecast. |
| `Returns!I4`, `I6` | The row labeled change in working capital reads free cash flow (`Values!I19`), then adds that cash flow to EBITDA and capex. In the first year: 13,802 + 9,969 − 48 = 23,723. | Derive cash operations from EBITDA, cash tax, capex, and the change in the working-capital balance. |
| `Returns!I22:P22` | First-year common proceeds use equity; later years use enterprise value. For example, `N22` references `N13` rather than the debt/cash-adjusted equity bridge. | Apply a consistent enterprise-to-equity bridge before all shareholder distributions. |
| `Returns!I14:P14` | Debt stays at the original 60,000 despite financing assumptions. | Roll both debt balances through interest, PIK, mandatory principal, revolver activity, and cash sweeps. |
| `Returns` exit-fee row and `LBO!D28` | Exit-fee cells are blank although an input fee rate of 3% exists. | Deduct fees on nonnegative exit enterprise value. |
| Preferred repayment/accrual/distribution rows | Preferred mechanics are blank although preferred equity is 90% of entry equity and its PIK rate is 8%. | Accrue sponsor-held preferred and pay it before ordinary shareholders. |
| `LBO!M18`, `U18` versus `S7`, `S8` | Sensitivity-table centers do not match the headline values at the same 8× entry/exit assumptions: IRR 42.6071% versus 38.3970%; MoM 7.9266× versus 6.6554×. Calculation mode is `autoNoTable`. | Do not use stale data-table caches as an oracle; the derivative uses explicit formulas and changed-input recalculation. |
| `Returns` forecast labels and cash-flow ranges | First forecast is labeled year zero; exit 5 selects December 2027. Return ranges omit the final available forecast column. | One-based periods, all eight periods supported; base exit period 5 is 1 December 2026. |
| `Returns!I42`, `I55` | Formulas reference blank `I184` to obtain zero. | Explicit zero opening cash and revolver balances. |

Three external links and externally targeted defined names exist. The observed formula references to external workbooks are labels (`LBO!B18`, `B20`, `Returns!B40`); the active numeric calculations inspected use local cells. Missing external files are **not** evidence that the numerical model cannot calculate. Iterative calculation is enabled, but that setting alone does not prove a numerical circularity.

The source's profile labels are not a reliable ordering constraint: its nominal upside assumptions can be below management assumptions. The derivative preserves the four numbered profiles rather than rewriting them to fit their labels.

## Explicit user decisions

1. Correct and validate the financial model, then evaluate Python replication. Do not score bug-for-bug replication of the original or ask candidates to infer undisclosed repairs.
2. Preserve the supplied **1 December** fiscal year-end, rather than silently changing it to 31 December.
3. Reconcile operating cash flow to operating drivers and working-capital changes, rather than preserving a separate free-cash-flow-margin forecast.

Consequently, historical source IRRs and sensitivity outputs are diagnostic evidence, **not expected answers** for this new task.

## Source-to-input mapping

- Deal date, last fiscal end, tax, entry/exit multiples, exit period and fee rate come from `LBO!D4`, `D5`, `D8`, `D16`, `D26:D28`.
- TLB and revolver assumptions come from source financing rows 40 and 39: principal/commitment, cash interest, PIK, maturity, amortization and sweep.
- Ordinary fraction, management ordinary ownership and preferred accrual use `LBO!P26`, `Q27`, `Q29`.
- Opening annual revenue and working capital use `Organic!G5` and `G47`: 171,697 and 6,653. They are explicit entry assumptions, with no invented interpolation to closing.
- Operating profiles use the source growth, gross-profit, opex and capex assumption blocks. First-year assumptions are common; subsequent years preserve the four selectable rows. Negative source capex is normalized into a positive expenditure input.
- Working-capital ratios use `Organic` working-capital balances divided by revenue for 2022–2026; the last supplied ratio is held constant for 2027–2029.
- Source monetary labels are inconsistent. The derivative consistently treats the supplied numeric units as **GBP thousands**; rescaling all monetary inputs must preserve investment multiples and returns.

## Deliberate conventions—not inferred legal terms

The [public task](../../tasks/pierre_lbo/task.md) freezes these choices before candidate runs:

- Opening-balance cash interest and TLB PIK avoid an average-balance circular model. Cash interest and PIK are simple ACT/365 accruals; preferred compounds at an effective annual ACT/365 rate.
- EBITDA and capex are prorated over owned operating days; working-capital balance movements are not. Entry and exit multiples use annual EBITDA.
- Cash tax uses positive cash EBITDA less cash interest. No D&A, tax-loss schedule, PIK deduction, or preferred deduction is modeled.
- Debt maturities are fiscal-period buckets. Revolver repayment precedes the term-loan cash sweep; mandatory obligations can be refinanced by the revolver only while borrowing capacity is available.
- A financing shortfall stops executed debt/cash schedules before the failed period, retains planned operations, and nulls all exit/waterfall/return outputs.
- The audited liquidity roundoff guard is `1e-12` times the largest current-row cash-flow/obligation/capacity operand, without an absolute floor. The prior absolute `1e-8` rule changed feasibility when an otherwise identical tiny deficit was currency-scaled; the public specification and both implementations now agree on the scale-relative rule.
- Sponsor preferred is paid first; management owns only its stated ordinary share. There are no interim dividends. Zero-investment MoM and zero-investment/zero-proceeds IRR are explicitly null.

This is a specified annual LBO exercise, not a complete transaction model or a certification of the author's original deal economics. Independent implementation agreement can detect coding errors; it cannot validate unstated commercial assumptions.

## Independent numerical qualification

`reference.py` implements the model with standard-library Python. `workbook.py` independently writes visible Excel formulas; it neither imports the Python valuation nor embeds calculated Python answers. Spreadsheet caches must be generated by a real calculation engine—openpyxl is not one. Native `XIRR` uses the actual dated cash flows and a near-root starting guess, not a cached Python IRR.

`qualify.py` compares every output field across the public base and changed-input scenarios, preserving per-case inputs, spreadsheet outputs, Python outputs, mismatches, engine identity, and hashes in a private report. Qualification results and any engine limitations must be reported separately from candidate-model scores.

The original is never opened for recalculation by this workflow. The public derivative contains the public base assumptions and four operating profiles, not the private changed-input bundles or reference implementation. Generated workbooks have no external links, macros, data tables or hidden sheets. The builder refuses frozen/source destinations and existing files to prevent accidental overwrite.

### Observed qualification and rounding boundary

Version 0.2 qualification passed all 55 fields across the public base and 45 changed-input scenarios, plus nine separate [hand-derived diagnostics](HAND_EXAMPLES.md), using **LibreOffice 26.8.0.3**. Native Excel 16.113.3 previously timed out; it was not retried during this audit, and no native Excel or visual-formatting verification is claimed. Current outputs and hashes are in [qualification.json](../../results/pierre_lbo/audit-2026-10-05/qualification.json); the original qualification remains in its dated historical evidence directory.

The first reconciliation found a preferred-hurdle discrepancy: Python retained an approximately `5.68e-15` management payout and returned nearly −100% IRR, whereas Calc produced zero payout and null IRR. Both implementations and the public specification now apply the same scale-relative rule: if `equity_proceeds - preferred_accrued <= 1e-12 * equity_proceeds`, allocate all proceeds to preferred and zero to ordinary. Otherwise pay accrued preferred and allocate the positive residual to ordinary. This conserves distributions and prevents floating-point dust from changing nullable-return semantics; the failing case remains in the suite.

The checked-in `tasks/pierre_lbo/pierre_lbo_one.xlsx` is the newly qualified version 0.2 **derivative only**. The original and detailed source inventory remain private. The [pretrial audit](../../analysis/pierre_lbo_audit.md) separates oracle evidence, deliberate-error controls, submission/isolation findings, engine limitations, and blocked candidate-trial prerequisites.
