import json
import sys

def solve():
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        return
    inp = json.loads(raw_input)

    current_ebit = float(inp["current_ebit"])
    current_capex = float(inp["current_capex"])
    current_depreciation = float(inp["current_depreciation"])
    tax_rate = float(inp["tax_rate"])
    current_revenues = float(inp["current_revenues"])
    current_noncash_working_capital = float(inp["current_noncash_working_capital"])
    change_working_capital = float(inp["change_working_capital"])
    cash_and_marketable_securities = float(inp["cash_and_marketable_securities"])
    equity_options_value = float(inp["equity_options_value"])
    prior_book_value_debt = float(inp["prior_book_value_debt"])
    prior_book_value_equity = float(inp["prior_book_value_equity"])
    market_price_per_share = float(inp["market_price_per_share"])
    shares_outstanding = float(inp["shares_outstanding"])
    market_value_debt = float(inp["market_value_debt"])
    high_growth_years = int(inp["high_growth_years"])
    beta = float(inp["beta"])
    riskfree_rate = float(inp["riskfree_rate"])
    risk_premium = float(inp["risk_premium"])
    pre_tax_cost_of_debt = float(inp["pre_tax_cost_of_debt"])
    ebit_five_years_ago = float(inp["ebit_five_years_ago"])
    outside_growth_rate = float(inp["outside_growth_rate"])
    stable_growth_rate = float(inp["stable_growth_rate"])
    stable_return_on_capital = float(inp["stable_return_on_capital"])

    growth_weights = inp.get("growth_weights") or {}
    w_hist = float(growth_weights.get("historical", 0.0))
    w_out = float(growth_weights.get("outside", 0.0))
    if "fundamental" in growth_weights:
        w_fund = float(growth_weights["fundamental"])
    else:
        w_fund = 1.0 - w_hist - w_out

    # 1. Discount-rate mechanics
    cost_of_equity = riskfree_rate + beta * risk_premium
    market_value_equity_weight_num = market_price_per_share * shares_outstanding
    equity_weight = market_value_equity_weight_num / (market_value_debt + market_value_equity_weight_num)
    after_tax_cost_of_debt = pre_tax_cost_of_debt * (1.0 - tax_rate)
    debt_weight = 1.0 - equity_weight
    wacc = cost_of_equity * equity_weight + after_tax_cost_of_debt * debt_weight
    stable_wacc = wacc

    # 2. Growth and reinvestment mechanics
    ebit_after_tax = current_ebit * (1.0 - tax_rate)
    current_fcff = (ebit_after_tax
                    - (current_capex - current_depreciation)
                    - change_working_capital)

    historical_growth_rate = (current_ebit / ebit_five_years_ago) ** 0.2 - 1.0
    fundamental_roc = ebit_after_tax / (prior_book_value_debt + prior_book_value_equity)
    fundamental_reinvestment_rate = (current_capex - current_depreciation + change_working_capital) / ebit_after_tax
    fundamental_growth_rate = fundamental_roc * fundamental_reinvestment_rate
    weighted_growth_rate = (historical_growth_rate * w_hist
                            + outside_growth_rate * w_out
                            + fundamental_growth_rate * w_fund)

    wc_ratio = current_noncash_working_capital / current_revenues
    working_capital_pct_revenue = 0.0 if wc_ratio < 0.0 else wc_ratio

    # 3. High-growth FCFF forecast
    high_growth_fcff = []
    high_growth_pv = []

    for t in range(1, high_growth_years + 1):
        growth_factor = (1.0 + weighted_growth_rate) ** t
        prev_growth_factor = (1.0 + weighted_growth_rate) ** (t - 1)
        ebit_t = ebit_after_tax * growth_factor
        net_capex_t = current_capex * growth_factor - current_depreciation * growth_factor
        chg_wc_t = current_revenues * working_capital_pct_revenue * (growth_factor - prev_growth_factor)
        fcff_t = ebit_t - net_capex_t - chg_wc_t
        pv_t = fcff_t / ((1.0 + wacc) ** t)
        high_growth_fcff.append(fcff_t)
        high_growth_pv.append(pv_t)

    # 4. Terminal-value mechanics
    stable_reinvestment_rate = stable_growth_rate / stable_return_on_capital
    terminal_ebit_after_tax = ebit_after_tax * ((1.0 + weighted_growth_rate) ** high_growth_years) * (1.0 + stable_growth_rate)
    terminal_fcff = terminal_ebit_after_tax * (1.0 - stable_reinvestment_rate)
    terminal_value = terminal_fcff / (stable_wacc - stable_growth_rate)

    pv_high_growth_fcff = sum(high_growth_pv)
    pv_terminal_value = terminal_value / ((1.0 + wacc) ** high_growth_years)

    # 5. Valuation bridge
    firm_value = pv_high_growth_fcff + pv_terminal_value
    market_value_equity = firm_value + cash_and_marketable_securities - market_value_debt
    equity_value_per_share = (market_value_equity - equity_options_value) / shares_outstanding

    result = {
        "cost_of_equity": cost_of_equity,
        "equity_weight": equity_weight,
        "after_tax_cost_of_debt": after_tax_cost_of_debt,
        "debt_weight": debt_weight,
        "wacc": wacc,
        "current_fcff": current_fcff,
        "historical_growth_rate": historical_growth_rate,
        "fundamental_roc": fundamental_roc,
        "fundamental_reinvestment_rate": fundamental_reinvestment_rate,
        "fundamental_growth_rate": fundamental_growth_rate,
        "weighted_growth_rate": weighted_growth_rate,
        "working_capital_pct_revenue": working_capital_pct_revenue,
        "high_growth_fcff": high_growth_fcff,
        "high_growth_pv": high_growth_pv,
        "stable_reinvestment_rate": stable_reinvestment_rate,
        "terminal_fcff": terminal_fcff,
        "stable_wacc": stable_wacc,
        "terminal_value": terminal_value,
        "pv_high_growth_fcff": pv_high_growth_fcff,
        "pv_terminal_value": pv_terminal_value,
        "firm_value": firm_value,
        "market_value_equity": market_value_equity,
        "equity_value_per_share": equity_value_per_share,
    }

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    solve()
