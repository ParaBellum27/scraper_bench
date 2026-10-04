"""Verified reference implementation for Task 001: Damodaran fcff2st.

This implementation reproduces the base-case logic in the supplied
`fcff2st.xlsx` workbook and is intentionally independent of Excel.

The initial benchmark freezes the workbook's switch settings and varies the
continuous assumptions in hidden tests. Later benchmark versions can expand
coverage to alternate Yes/No branches in the spreadsheet.
"""


def value_company(inputs):
    ebit = float(inputs["current_ebit"])
    tax_rate = float(inputs["tax_rate"])
    capex = float(inputs["current_capex"])
    depreciation = float(inputs["current_depreciation"])
    revenues = float(inputs["current_revenues"])
    noncash_wc = float(inputs["current_noncash_working_capital"])
    cash = float(inputs["cash_and_marketable_securities"])
    equity_options = float(inputs["equity_options_value"])
    market_debt = float(inputs["market_value_debt"])
    share_price = float(inputs["market_price_per_share"])
    shares = float(inputs["shares_outstanding"])
    beta = float(inputs["beta"])
    riskfree_rate = float(inputs["riskfree_rate"])
    risk_premium = float(inputs["risk_premium"])
    pre_tax_cost_debt = float(inputs["pre_tax_cost_of_debt"])
    high_growth_years = int(inputs["high_growth_years"])
    stable_growth = float(inputs["stable_growth_rate"])
    stable_roic = float(inputs["stable_return_on_capital"])

    roc = float(inputs["fundamental_roc"])
    reinvestment_rate = float(inputs["fundamental_reinvestment_rate"])
    historical_growth = float(inputs["historical_growth_rate"])
    outside_growth = float(inputs["outside_growth_rate"])
    weights = inputs["growth_weights"]

    fundamental_growth = roc * reinvestment_rate
    high_growth = (
        historical_growth * float(weights["historical"])
        + outside_growth * float(weights["outside"])
        + fundamental_growth * float(weights["fundamental"])
    )

    cost_of_equity = riskfree_rate + beta * risk_premium
    market_equity = share_price * shares
    equity_weight = market_equity / (market_equity + market_debt)
    debt_weight = 1.0 - equity_weight
    after_tax_cost_debt = pre_tax_cost_debt * (1.0 - tax_rate)
    wacc = cost_of_equity * equity_weight + after_tax_cost_debt * debt_weight

    wc_pct_revenues = noncash_wc / revenues
    current_ebit_after_tax = ebit * (1.0 - tax_rate)

    yearly = []
    pv_high_growth = 0.0
    for year in range(1, high_growth_years + 1):
        ebit_after_tax = current_ebit_after_tax * (1.0 + high_growth) ** year
        capex_minus_depr = (
            capex * (1.0 + high_growth) ** year
            - depreciation * (1.0 + high_growth) ** year
        )
        change_wc = (
            revenues
            * wc_pct_revenues
            * ((1.0 + high_growth) ** year - (1.0 + high_growth) ** (year - 1))
        )
        fcff = ebit_after_tax - capex_minus_depr - change_wc
        present_value = fcff / (1.0 + wacc) ** year
        pv_high_growth += present_value
        yearly.append(
            {
                "year": year,
                "ebit_after_tax": ebit_after_tax,
                "capex_minus_depreciation": capex_minus_depr,
                "change_working_capital": change_wc,
                "fcff": fcff,
                "present_value": present_value,
            }
        )

    terminal_ebit_after_tax = (
        current_ebit_after_tax
        * (1.0 + high_growth) ** high_growth_years
        * (1.0 + stable_growth)
    )
    terminal_change_wc = (
        revenues
        * (1.0 + high_growth) ** high_growth_years
        * stable_growth
        * wc_pct_revenues
    )
    terminal_capex_minus_depr = (
        stable_growth / stable_roic * terminal_ebit_after_tax - terminal_change_wc
    )
    terminal_fcff = (
        terminal_ebit_after_tax - terminal_capex_minus_depr - terminal_change_wc
    )
    terminal_value = terminal_fcff / (wacc - stable_growth)
    pv_terminal_value = terminal_value / (1.0 + wacc) ** high_growth_years

    firm_value = pv_high_growth + pv_terminal_value
    market_value_equity = firm_value + cash - market_debt
    equity_value_after_options = market_value_equity - equity_options
    value_per_share = equity_value_after_options / shares

    return {
        "fundamental_growth_rate": fundamental_growth,
        "high_growth_rate": high_growth,
        "cost_of_equity": cost_of_equity,
        "equity_weight": equity_weight,
        "after_tax_cost_of_debt": after_tax_cost_debt,
        "debt_weight": debt_weight,
        "wacc": wacc,
        "working_capital_pct_revenues": wc_pct_revenues,
        "yearly": yearly,
        "terminal_ebit_after_tax": terminal_ebit_after_tax,
        "terminal_capex_minus_depreciation": terminal_capex_minus_depr,
        "terminal_change_working_capital": terminal_change_wc,
        "terminal_fcff": terminal_fcff,
        "terminal_value": terminal_value,
        "pv_high_growth_fcff": pv_high_growth,
        "pv_terminal_value": pv_terminal_value,
        "firm_value": firm_value,
        "cash_and_marketable_securities": cash,
        "market_value_debt": market_debt,
        "market_value_equity": market_value_equity,
        "equity_options_value": equity_options,
        "value_per_share": value_per_share,
    }
