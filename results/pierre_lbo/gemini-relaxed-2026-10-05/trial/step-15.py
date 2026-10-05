required_fields = [
    # Status and timing
    "status", "failure_period", "funding_shortfall", "dates", "operating_fractions", "interest_year_fractions", "exit_date", "holding_period_years",
    # Initial funding
    "entry_ebitda", "entry_ev", "entry_equity", "ordinary_equity", "preferred_equity", "sponsor_investment", "management_investment",
    # Forecast arrays
    "revenue", "gross_profit", "opex", "ebitda", "ebitda_margin", "working_capital", "change_working_capital", "cash_capex", "cash_ebitda",
    # Financing arrays
    "cash_interest", "tlb_interest", "rcf_interest", "cash_taxes", "pre_financing_cash_flow", "tlb_pik", "mandatory_tlb_repayment", "mandatory_rcf_repayment", "rcf_draw", "rcf_repayment", "tlb_sweep", "tlb_balance", "rcf_balance", "cash_balance",
    # Exit bridge
    "exit_ev", "exit_fees", "exit_debt", "exit_cash", "equity_value_before_floor", "equity_proceeds",
    # Waterfall and returns
    "preferred_accrued", "preferred_payout", "ordinary_payout", "sponsor_proceeds", "management_proceeds", "deal_mom", "sponsor_mom", "management_mom", "deal_irr", "sponsor_irr", "management_irr"
]

print("Count:", len(required_fields))
print("Unique count:", len(set(required_fields)))
assert len(required_fields) == 55
