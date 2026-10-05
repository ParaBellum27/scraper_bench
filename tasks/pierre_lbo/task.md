# Pierre LBO One — corrected leveraged buyout replication

Implement the financial model in `pierre_lbo_one.xlsx` as one self-contained Python program, `solution.py`. Read one JSON object from stdin and print one JSON object to stdout. Use the input values supplied at runtime; do not hard-code the public base case or read the workbook during evaluation. The evaluation workspace contains only your submitted file and runtime input, with no network access.

The workbook is a **corrected derivative**, not a bug-for-bug copy of the author's original. Its visible formulas define the model. `inputs/base_case.json` supplies its public assumptions. No hidden evaluation inputs or reference code are available during development.

## Model and input conventions

- Monetary amounts use consistent GBP-thousands units. Rates and ownership shares are decimals. `capex` is a positive cash expenditure.
- `case` selects one of four eight-period profiles in `scenarios` (one-based). Each profile supplies `revenue_growth`, `gross_profit_margin`, `opex_margin`, and `capex`. The common `working_capital_ratio` has eight values.
- Opening revenue and working capital are explicit entry assumptions. Opening cash and revolver borrowings are zero. Entry funding is term-loan principal plus equity; there are no entry fees. Entry valuation uses **first forecast annual EBITDA**, not stub cash EBITDA.
- `last_fiscal_year_end` and `deal_date` are ISO dates. Keep the supplied fiscal date, including **1 December** in the base case. Advance fiscal ends sequentially with Excel's `EDATE(previous,12)` month-end clamping; do not substitute 31 December.
- `exit_period` is 1–8. **Period 1 is the first post-close fiscal end**, not year zero. All forecast/timing arrays end at the selected exit period.
- First-period cash EBITDA and capex are prorated by owned days divided by the full fiscal period's days. Later full periods have operating fraction 1, including leap years. Apply the **full working-capital balance movement**, not a prorated movement.
- Cash interest and term-loan PIK use opening balances and actual owned days/365. Do not introduce average-balance circularity. No revolver PIK.
- Cash tax is `max(cash_ebitda - cash_interest, 0) * tax_rate`. There is no D&A, loss carryforward, tax refund, or deduction for term-loan PIK or preferred accrual. `pre_financing_cash_flow` is after capex, working-capital movement, and cash taxes, but **before cash interest and principal**.
- Term-loan amortization uses original principal times the annual amortization rate times the operating fraction, capped at outstanding principal plus current PIK. At or after its maturity period, all remaining term-loan principal and PIK are due instead. Maturity is a fiscal-period bucket, not a legal anniversary date.
- Revolver borrowings can fund operating deficits, cash interest, and mandatory principal, only within available commitment. At or after revolver maturity, opening borrowings are due and no new borrowing is allowed.
- Pay mandatory principal first, then voluntarily repay outstanding revolver borrowings, then apply the term-loan cash-sweep fraction to remaining cash, capped at outstanding term debt. Carry residual cash forward. `rcf_repayment` includes **both mandatory and voluntary** repayments; `tlb_sweep` excludes scheduled/maturity principal.
- Exit enterprise value uses exit-period **annual** EBITDA and the exit multiple. Exit fees apply only to nonnegative enterprise value. Deduct fees and both closing debt balances, add closing cash, and floor distributable equity proceeds at zero.
- All preferred equity belongs to the sponsor. It compounds at the effective annual preferred PIK rate over actual holding days/365, and is paid first up to available proceeds. Split only the residual ordinary proceeds using the management ordinary-ownership fraction.
- **Preferred-hurdle rounding:** if `equity_proceeds - preferred_accrued <= 1e-12 * equity_proceeds`, allocate all equity proceeds to preferred and zero to ordinary. Otherwise pay the preferred accrual and distribute the positive residual to ordinary. This scale-relative roundoff rule prevents a numerical dust payout from turning an undefined management IRR into almost −100%, while conserving total distributions.
- There are no interim distributions. MoM is terminal proceeds divided by initial investment. IRR is the actual-date annualized return (the two-cash-flow equivalent of Excel XIRR), **not** an integer-year CAGR. MoM is `null` for zero investment. IRR is `null` for zero investment or nonpositive proceeds; do not substitute zero or −100% for this undefined-return convention.

### Liquidity failure

If the revolver draw required to meet all current obligations exceeds available borrowing capacity by **more than 1e-8 monetary units**, return `status: "liquidity_shortfall"`, its one-based `failure_period`, and `funding_shortfall` equal to the excess required draw. Stop financing before executing the failed row.

Keep the full planned forecast and timing arrays, initial funding, planned `exit_date`, and `holding_period_years`. Financing arrays contain **only successfully financed preceding periods**; they can be empty. Every exit, waterfall, MoM, and IRR field is `null`. Do not fabricate financed balances or repayments for the failed period. A residual shortage within 1e-8 is floating-point rounding: cap borrowing at capacity and floor residual cash at zero.

For a financed exit, return `status: "ok"`, `failure_period: null`, and `funding_shortfall: 0`.

### Input domain

Evaluated inputs have exactly the public JSON structure, four profiles, and eight values per vector. Numeric inputs are finite, not booleans. Revenue is positive; growth is greater than −1; opening working capital, capex, working-capital ratios, interest/PIK rates, debt amounts, commitments and multiples are nonnegative. Margins, tax/fee rates, ownership shares, amortization and sweep rates are in [0,1]. Maturity periods are positive integers. Closing is strictly between the last and next fiscal end. Derived entry equity is strictly positive. Financial insolvency is a valid scenario, not an invalid input. No malformed-input error protocol is scored.

## Required output: 55 flat fields

Do not nest results by sheet. All numbers must be JSON numbers, never numeric strings. Dates must be `YYYY-MM-DD` strings. Use JSON `null`, not NaN or infinity.

| Group | Fields |
|---|---|
| Status and timing | `status`, `failure_period`, `funding_shortfall`, `dates`, `operating_fractions`, `interest_year_fractions`, `exit_date`, `holding_period_years` |
| Initial funding | `entry_ebitda`, `entry_ev`, `entry_equity`, `ordinary_equity`, `preferred_equity`, `sponsor_investment`, `management_investment` |
| Forecast arrays | `revenue`, `gross_profit`, `opex`, `ebitda`, `ebitda_margin`, `working_capital`, `change_working_capital`, `cash_capex`, `cash_ebitda` |
| Financing arrays | `cash_interest`, `tlb_interest`, `rcf_interest`, `cash_taxes`, `pre_financing_cash_flow`, `tlb_pik`, `mandatory_tlb_repayment`, `mandatory_rcf_repayment`, `rcf_draw`, `rcf_repayment`, `tlb_sweep`, `tlb_balance`, `rcf_balance`, `cash_balance` |
| Exit bridge | `exit_ev`, `exit_fees`, `exit_debt`, `exit_cash`, `equity_value_before_floor`, `equity_proceeds` |
| Waterfall and returns | `preferred_accrued`, `preferred_payout`, `ordinary_payout`, `sponsor_proceeds`, `management_proceeds`, `deal_mom`, `sponsor_mom`, `management_mom`, `deal_irr`, `sponsor_irr`, `management_irr` |

`dates`, `operating_fractions`, and `interest_year_fractions` are arrays. Other timing fields and all funding, exit, waterfall and return fields are scalars. `equity_value_before_floor` is the signed exit equity bridge; `equity_proceeds` is its nonnegative distribution floor. `ebitda_margin` is gross-profit margin minus opex margin.

## Workbook navigation

- **Inputs**: scalar inputs and working-capital ratios.
- **Scenarios**: four operating profiles, ordered by case then period.
- **Forecast**: annual operating forecast, dates, stub fractions and cash operations.
- **Debt**: obligations, funding feasibility, executed flows and closing balances.
- **Returns**: entry funding, status, exit bridge, preferred waterfall and dated XIRR cash flows.

Blank formula outputs in inactive or infeasible workbook rows do not mean numeric zero. Use the array-prefix and `null` rules above.

## Scoring

Each case weights status/timing 5%, initial funding 10%, operations 25%, debt/cash 30%, exit bridge 15%, and waterfall/returns 15%. Fields have equal weight within their group; array elements have equal weight within their field, but array lengths must match. Strings and nulls must match exactly. Numeric comparisons use relative tolerance 1e-7 and absolute tolerance 1e-7.

The public base case contributes 20%; changed-input cases contribute 80%. Expect changes in operating profiles, financing, tax, fees, ownership, timing, and currency scale, including infeasible financing and zero-investment/zero-payout boundaries. Matching only the public base case is insufficient.

Reports distinguish **fully correct cases** (all required fields match within their stated tolerances) from cases scoring at least 95. A high partial-credit score does not establish financial correctness.
