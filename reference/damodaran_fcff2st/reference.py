"""Reference implementation of Damodaran's fcff2st two-stage FCFF model.

Implements the fixed-switch configuration used by Task 001. Formulas are
transcribed from the supplied fcff2st.xlsx workbook and cross-checked against
Damodaran's published FCFF methodology.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _require(inputs: Dict[str, Any], key: str) -> float:
    if key not in inputs:
        raise KeyError(f"missing required input: {key}")
    return float(inputs[key])


def value_company(inputs: Dict[str, Any]) -> Dict[str, Any]:
    ebit = _require(inputs, "current_ebit")
    capex = _require(inputs, "current_capex")
    depreciation = _require(inputs, "current_depreciation")
    tax_rate = _require(inputs, "tax_rate")
    revenues = _require(inputs, "current_revenues")
    noncash_wc = _require(inputs, "current_noncash_working_capital")
    change_wc = _require(inputs, "change_working_capital")

    cash = _require(inputs, "cash_and_marketable_securities")
    options_value = _require(inputs, "equity_options_value")
    market_price = _require(inputs, "market_price_per_share")
    shares = _require(inputs, "shares_outstanding")
    market_debt = _require(inputs, "market_value_debt")

    years = int(inputs["high_growth_years"])
    if years < 1 or years > 10:
        raise ValueError("high_growth_years must be between 1 and 10")
    beta = _require(inputs, "beta")
    riskfree = _require(inputs, "riskfree_rate")
    risk_premium = _require(inputs, "risk_premium")
    pretax_cost_debt = _require(inputs, "pre_tax_cost_of_debt")

    ebit_5y_ago = _require(inputs, "ebit_five_years_ago")
    prior_debt = _require(inputs, "prior_book_value_debt")
    prior_equity = _require(inputs, "prior_book_value_equity")
    outside_growth = _require(inputs, "outside_growth_rate")
    weights = inputs["growth_weights"]
    w_hist = float(weights["historical"])
    w_out = float(weights["outside"])
    w_fund = float(weights["fundamental"])
    if abs((w_hist + w_out + w_fund) - 1.0) > 1e-9:
        raise ValueError("growth_weights must sum to 1")

    stable_growth = _require(inputs, "stable_growth_rate")
    stable_roc = _require(inputs, "stable_return_on_capital")
    if stable_roc <= 0:
        raise ValueError("stable_return_on_capital must be positive")

    cost_of_equity = riskfree + beta * risk_premium
    market_equity_for_weight = market_price * shares
    equity_weight = market_equity_for_weight / (market_debt + market_equity_for_weight)
    debt_weight = 1.0 - equity_weight
    after_tax_cost_debt = pretax_cost_debt * (1.0 - tax_rate)
    wacc = cost_of_equity * equity_weight + after_tax_cost_debt * debt_weight

    current_after_tax_ebit = ebit * (1.0 - tax_rate)
    current_net_capex = capex - depreciation
    current_fcff = current_after_tax_ebit - current_net_capex - change_wc

    historical_growth_rate = (ebit / ebit_5y_ago) ** 0.2 - 1.0
    fundamental_roc = current_after_tax_ebit / (prior_debt + prior_equity)
    fundamental_reinvestment_rate = (capex - depreciation + change_wc) / current_after_tax_ebit
    fundamental_growth_rate = fundamental_roc * fundamental_reinvestment_rate
    weighted_growth_rate = (
        historical_growth_rate * w_hist
        + outside_growth * w_out
        + fundamental_growth_rate * w_fund
    )

    working_capital_pct_revenue = max(noncash_wc / revenues, 0.0)

    high_growth_fcff: List[float] = []
    high_growth_pv: List[float] = []
    for year in range(1, years + 1):
        after_tax_ebit_y = current_after_tax_ebit * (1.0 + weighted_growth_rate) ** year
        net_capex_y = (
            capex * (1.0 + weighted_growth_rate) ** year
            - depreciation * (1.0 + weighted_growth_rate) ** year
        )
        change_wc_y = (
            revenues
            * working_capital_pct_revenue
            * ((1.0 + weighted_growth_rate) ** year - (1.0 + weighted_growth_rate) ** (year - 1))
        )
        fcff_y = after_tax_ebit_y - net_capex_y - change_wc_y
        pv_y = fcff_y / (1.0 + wacc) ** year
        high_growth_fcff.append(fcff_y)
        high_growth_pv.append(pv_y)

    terminal_after_tax_ebit = (
        current_after_tax_ebit
        * (1.0 + weighted_growth_rate) ** years
        * (1.0 + stable_growth)
    )
    revenue_at_end_high_growth = revenues * (1.0 + weighted_growth_rate) ** years
    terminal_change_wc = (
        revenue_at_end_high_growth * (1.0 + stable_growth) - revenue_at_end_high_growth
    ) * working_capital_pct_revenue

    stable_reinvestment_rate = stable_growth / stable_roc
    terminal_net_capex = stable_reinvestment_rate * terminal_after_tax_ebit - terminal_change_wc
    terminal_fcff = terminal_after_tax_ebit - terminal_net_capex - terminal_change_wc

    stable_wacc = wacc
    if stable_growth >= stable_wacc:
        raise ValueError("stable_growth_rate must be below stable WACC")
    terminal_value = terminal_fcff / (stable_wacc - stable_growth)

    pv_high_growth_fcff = sum(high_growth_pv)
    pv_terminal_value = terminal_value / (1.0 + wacc) ** years
    firm_value = pv_high_growth_fcff + pv_terminal_value
    market_value_equity = firm_value + cash - market_debt
    equity_value_per_share = (market_value_equity - options_value) / shares

    return {
        "cost_of_equity": cost_of_equity,
        "equity_weight": equity_weight,
        "after_tax_cost_of_debt": after_tax_cost_debt,
        "debt_weight": debt_weight,
        "wacc": wacc,
        "current_after_tax_ebit": current_after_tax_ebit,
        "current_fcff": current_fcff,
        "historical_growth_rate": historical_growth_rate,
        "fundamental_roc": fundamental_roc,
        "fundamental_reinvestment_rate": fundamental_reinvestment_rate,
        "fundamental_growth_rate": fundamental_growth_rate,
        "weighted_growth_rate": weighted_growth_rate,
        "working_capital_pct_revenue": working_capital_pct_revenue,
        "high_growth_fcff": high_growth_fcff,
        "high_growth_pv": high_growth_pv,
        "stable_growth_rate": stable_growth,
        "stable_reinvestment_rate": stable_reinvestment_rate,
        "terminal_after_tax_ebit": terminal_after_tax_ebit,
        "terminal_change_working_capital": terminal_change_wc,
        "terminal_net_capex": terminal_net_capex,
        "terminal_fcff": terminal_fcff,
        "stable_wacc": stable_wacc,
        "terminal_value": terminal_value,
        "pv_high_growth_fcff": pv_high_growth_fcff,
        "pv_terminal_value": pv_terminal_value,
        "firm_value": firm_value,
        "market_value_equity": market_value_equity,
        "equity_value_per_share": equity_value_per_share,
    }
