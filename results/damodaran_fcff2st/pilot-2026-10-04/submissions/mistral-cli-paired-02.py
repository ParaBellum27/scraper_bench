import json
import sys

def main():
    input_data = json.load(sys.stdin)
    
    # Extract all inputs
    current_ebit = input_data['current_ebit']
    current_capex = input_data['current_capex']
    current_depreciation = input_data['current_depreciation']
    tax_rate = input_data['tax_rate']
    current_revenues = input_data['current_revenues']
    current_noncash_working_capital = input_data['current_noncash_working_capital']
    change_working_capital = input_data['change_working_capital']
    prior_book_value_debt = input_data['prior_book_value_debt']
    prior_book_value_equity = input_data['prior_book_value_equity']
    market_price_per_share = input_data['market_price_per_share']
    shares_outstanding = input_data['shares_outstanding']
    market_value_debt = input_data['market_value_debt']
    cash_and_marketable_securities = input_data['cash_and_marketable_securities']
    equity_options_value = input_data.get('equity_options_value', 0)
    high_growth_years = input_data['high_growth_years']
    beta = input_data['beta']
    riskfree_rate = input_data['riskfree_rate']
    risk_premium = input_data['risk_premium']
    pre_tax_cost_of_debt = input_data['pre_tax_cost_of_debt']
    ebit_five_years_ago = input_data['ebit_five_years_ago']
    outside_growth_rate = input_data['outside_growth_rate']
    growth_weights = input_data['growth_weights']
    stable_growth_rate = input_data['stable_growth_rate']
    stable_return_on_capital = input_data['stable_return_on_capital']
    
    # Cost of Equity (CAPM)
    cost_of_equity = riskfree_rate + beta * risk_premium
    
    # Market value of equity
    market_value_equity_input = market_price_per_share * shares_outstanding
    
    # Equity weight (market-value basis)
    equity_weight = market_value_equity_input / (market_value_debt + market_value_equity_input)
    
    # After-tax cost of debt
    after_tax_cost_of_debt = pre_tax_cost_of_debt * (1 - tax_rate)
    
    # Debt weight
    debt_weight = 1 - equity_weight
    
    # WACC
    wacc = cost_of_equity * equity_weight + after_tax_cost_of_debt * debt_weight
    
    # Current FCFF
    ebit_after_tax = current_ebit * (1 - tax_rate)
    net_capex = current_capex - current_depreciation
    current_fcff = ebit_after_tax - net_capex - change_working_capital
    
    # Historical Growth Rate (5-year CAGR)
    historical_growth_rate = (current_ebit / ebit_five_years_ago) ** (0.2) - 1
    
    # Fundamental ROC
    prior_total_capital = prior_book_value_debt + prior_book_value_equity
    fundamental_roc = ebit_after_tax / prior_total_capital
    
    # Fundamental Reinvestment Rate
    fundamental_reinvestment_rate = (current_capex - current_depreciation + change_working_capital) / ebit_after_tax
    
    # Fundamental Growth Rate
    fundamental_growth_rate = fundamental_roc * fundamental_reinvestment_rate
    
    # Weighted Growth Rate
    historical_weight = growth_weights['historical']
    outside_weight = growth_weights['outside']
    fundamental_weight = growth_weights['fundamental']
    weighted_growth_rate = (historical_growth_rate * historical_weight +
                            outside_growth_rate * outside_weight +
                            fundamental_growth_rate * fundamental_weight)
    
    # Working Capital as % of Revenue
    working_capital_pct_revenue = current_noncash_working_capital / current_revenues
    
    # High Growth Period Calculations
    high_growth_fcff = []
    high_growth_pv = []
    
    for year in range(1, high_growth_years + 1):
        revenue_t = current_revenues * (1 + weighted_growth_rate) ** year
        ebit_t = current_ebit * (1 + weighted_growth_rate) ** year
        capex_t = current_capex * (1 + weighted_growth_rate) ** year
        depreciation_t = current_depreciation * (1 + weighted_growth_rate) ** year
        
        ebit_after_tax_t = ebit_t * (1 - tax_rate)
        net_capex_t = capex_t - depreciation_t
        
        revenue_t_minus_1 = current_revenues * (1 + weighted_growth_rate) ** (year - 1)
        wc_t = revenue_t * working_capital_pct_revenue
        wc_t_minus_1 = revenue_t_minus_1 * working_capital_pct_revenue
        change_wc_t = wc_t - wc_t_minus_1
        
        fcff_t = ebit_after_tax_t - net_capex_t - change_wc_t
        high_growth_fcff.append(fcff_t)
        
        pv_t = fcff_t / (1 + wacc) ** year
        high_growth_pv.append(pv_t)
    
    # Terminal Value Calculations
    ebit_end_hg = current_ebit * (1 + weighted_growth_rate) ** high_growth_years
    ebit_stable = ebit_end_hg * (1 + stable_growth_rate)
    ebit_after_tax_stable = ebit_stable * (1 - tax_rate)
    
    stable_reinvestment_rate = stable_growth_rate / stable_return_on_capital
    terminal_fcff = ebit_after_tax_stable * (1 - stable_reinvestment_rate)
    
    stable_wacc = wacc
    terminal_value = terminal_fcff / (stable_wacc - stable_growth_rate)
    
    pv_terminal_value = terminal_value / (1 + wacc) ** high_growth_years
    pv_high_growth_fcff = sum(high_growth_pv)
    
    firm_value = pv_high_growth_fcff + pv_terminal_value
    market_value_equity = firm_value + cash_and_marketable_securities - market_value_debt
    equity_value_per_share = (market_value_equity - equity_options_value) / shares_outstanding
    
    output = {
        'cost_of_equity': cost_of_equity,
        'equity_weight': equity_weight,
        'after_tax_cost_of_debt': after_tax_cost_of_debt,
        'debt_weight': debt_weight,
        'wacc': wacc,
        'current_fcff': current_fcff,
        'historical_growth_rate': historical_growth_rate,
        'fundamental_roc': fundamental_roc,
        'fundamental_reinvestment_rate': fundamental_reinvestment_rate,
        'fundamental_growth_rate': fundamental_growth_rate,
        'weighted_growth_rate': weighted_growth_rate,
        'working_capital_pct_revenue': working_capital_pct_revenue,
        'high_growth_fcff': high_growth_fcff,
        'high_growth_pv': high_growth_pv,
        'stable_reinvestment_rate': stable_reinvestment_rate,
        'terminal_fcff': terminal_fcff,
        'stable_wacc': stable_wacc,
        'terminal_value': terminal_value,
        'pv_high_growth_fcff': pv_high_growth_fcff,
        'pv_terminal_value': pv_terminal_value,
        'firm_value': firm_value,
        'market_value_equity': market_value_equity,
        'equity_value_per_share': equity_value_per_share
    }
    
    print(json.dumps(output))

if __name__ == '__main__':
    main()