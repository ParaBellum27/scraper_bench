import json, calendar
from datetime import date, datetime
import openpyxl

def edate_12(dt):
    y = dt.year + 1
    m = dt.month
    max_days = calendar.monthrange(y, m)[1]
    d = min(dt.day, max_days)
    return date(y, m, d)

def parse_date(d_str):
    if isinstance(d_str, (datetime, date)):
        return date(d_str.year, d_str.month, d_str.day)
    return datetime.strptime(str(d_str)[:10], "%Y-%m-%d").date()

def solve(inputs):
    case_idx = inputs['case'] - 1
    scenario = inputs['scenarios'][case_idx]
    
    last_fye = parse_date(inputs['last_fiscal_year_end'])
    deal_dt = parse_date(inputs['deal_date'])
    exit_p = inputs['exit_period']
    
    # Precompute dates and timing for all exit_period periods
    dates = []
    operating_fractions = []
    interest_year_fractions = []
    
    curr_fye = last_fye
    for p in range(1, exit_p + 1):
        prev_fye = curr_fye
        curr_fye = edate_12(prev_fye)
        dates.append(curr_fye.strftime("%Y-%m-%d"))
        
        # Cash flow start
        cf_start = deal_dt if p == 1 else prev_fye
        # Operating fraction
        op_frac = (curr_fye - cf_start).days / (curr_fye - prev_fye).days
        operating_fractions.append(op_frac)
        # Interest year fraction
        int_frac = (curr_fye - cf_start).days / 365.0
        interest_year_fractions.append(int_frac)
        
    exit_date = dates[exit_p - 1]
    holding_period_years = (parse_date(exit_date) - deal_dt).days / 365.0
    
    # Forecast arrays
    revenue = []
    gross_profit = []
    opex = []
    ebitda = []
    ebitda_margin = []
    working_capital = []
    change_working_capital = []
    cash_capex = []
    cash_ebitda = []
    
    curr_rev = inputs['opening_revenue']
    curr_wc = inputs['opening_working_capital']
    
    for i in range(exit_p):
        g = scenario['revenue_growth'][i]
        gp_m = scenario['gross_profit_margin'][i]
        op_m = scenario['opex_margin'][i]
        cpx = scenario['capex'][i]
        wc_r = inputs['working_capital_ratio'][i]
        
        rev = (inputs['opening_revenue'] if i == 0 else revenue[i-1]) * (1.0 + g)
        gp = rev * gp_m
        op = rev * op_m
        eb = gp - op
        eb_m = gp_m - op_m
        wc = rev * wc_r
        c_wc = wc - (inputs['opening_working_capital'] if i == 0 else working_capital[i-1])
        c_cpx = cpx * operating_fractions[i]
        c_eb = eb * operating_fractions[i]
        
        revenue.append(rev)
        gross_profit.append(gp)
        opex.append(op)
        ebitda.append(eb)
        ebitda_margin.append(eb_m)
        working_capital.append(wc)
        change_working_capital.append(c_wc)
        cash_capex.append(c_cpx)
        cash_ebitda.append(c_eb)
        
    # Initial funding
    entry_ebitda = ebitda[0]
    entry_ev = entry_ebitda * inputs['entry_multiple']
    entry_equity = entry_ev - inputs['term_loan']['principal']
    ordinary_equity = entry_equity * inputs['ordinary_equity_fraction']
    preferred_equity = entry_equity - ordinary_equity
    management_investment = ordinary_equity * inputs['management_ordinary_fraction']
    sponsor_investment = entry_equity - management_investment
    
    # Financing arrays
    cash_interest = []
    tlb_interest = []
    rcf_interest = []
    cash_taxes = []
    pre_financing_cash_flow = []
    tlb_pik = []
    mandatory_tlb_repayment = []
    mandatory_rcf_repayment = []
    rcf_draw = []
    rcf_repayment = []
    tlb_sweep = []
    tlb_balance = []
    rcf_balance = []
    cash_balance = []
    
    status = "ok"
    failure_period = None
    funding_shortfall = 0
    
    tl = inputs['term_loan']
    rcf = inputs['revolver']
    tax_rate = inputs['tax_rate']
    
    for p in range(1, exit_p + 1):
        i = p - 1
        opening_tlb = tl['principal'] if p == 1 else tlb_balance[i-1]
        opening_rcf = 0.0 if p == 1 else rcf_balance[i-1]
        opening_cash = 0.0 if p == 1 else cash_balance[i-1]
        
        tlb_int = opening_tlb * tl['cash_rate'] * interest_year_fractions[i]
        rcf_int = opening_rcf * rcf['cash_rate'] * interest_year_fractions[i]
        cash_int = tlb_int + rcf_int
        tlb_pik_val = opening_tlb * tl['pik_rate'] * interest_year_fractions[i]
        
        cash_tax = max(cash_ebitda[i] - cash_int, 0.0) * tax_rate
        pcf = cash_ebitda[i] - cash_capex[i] - change_working_capital[i] - cash_tax
        
        if p >= tl['maturity_period']:
            prop_mand_tlb = opening_tlb + tlb_pik_val
        else:
            prop_mand_tlb = min(opening_tlb + tlb_pik_val, tl['principal'] * tl['amortization_rate'] * operating_fractions[i])
            
        if p >= rcf['maturity_period']:
            prop_mand_rcf = opening_rcf
        else:
            prop_mand_rcf = 0.0
            
        cash_before_rep = opening_cash + pcf - cash_int
        req_draw = max(prop_mand_tlb + prop_mand_rcf - cash_before_rep, 0.0)
        
        if p < rcf['maturity_period']:
            avail_draw = max(rcf['commitment'] - opening_rcf, 0.0)
        else:
            avail_draw = 0.0
            
        pot_shortfall = max(req_draw - avail_draw, 0.0)
        liq_scale = max(opening_cash, abs(cash_ebitda[i]), cash_capex[i], abs(change_working_capital[i]),
                        cash_tax, cash_int, prop_mand_tlb + prop_mand_rcf, avail_draw)
        
        if pot_shortfall > 1e-12 * liq_scale:
            status = "liquidity_shortfall"
            failure_period = p
            funding_shortfall = pot_shortfall
            break
            
        # Execute flows
        rcf_dr = min(req_draw, avail_draw)
        cash_after_mand = max(cash_before_rep + rcf_dr - prop_mand_tlb - prop_mand_rcf, 0.0)
        interim_rcf = opening_rcf + rcf_dr - prop_mand_rcf
        vol_rcf_rep = min(cash_after_mand, interim_rcf)
        rcf_rep_tot = prop_mand_rcf + vol_rcf_rep
        cash_after_rcf = cash_after_mand - vol_rcf_rep
        tlb_swp = min(cash_after_rcf * tl['cash_sweep'], opening_tlb + tlb_pik_val - prop_mand_tlb)
        tlb_bal = opening_tlb + tlb_pik_val - prop_mand_tlb - tlb_swp
        rcf_bal = interim_rcf - vol_rcf_rep
        cash_bal = max(cash_after_rcf - tlb_swp, 0.0)
        
        cash_interest.append(cash_int)
        tlb_interest.append(tlb_int)
        rcf_interest.append(rcf_int)
        cash_taxes.append(cash_tax)
        pre_financing_cash_flow.append(pcf)
        tlb_pik.append(tlb_pik_val)
        mandatory_tlb_repayment.append(prop_mand_tlb)
        mandatory_rcf_repayment.append(prop_mand_rcf)
        rcf_draw.append(rcf_dr)
        rcf_repayment.append(rcf_rep_tot)
        tlb_sweep.append(tlb_swp)
        tlb_balance.append(tlb_bal)
        rcf_balance.append(rcf_bal)
        cash_balance.append(cash_bal)
        
    if status == "ok":
        exit_ev = ebitda[exit_p - 1] * inputs['exit_multiple']
        exit_fees = max(exit_ev, 0.0) * inputs['exit_fee_rate']
        exit_debt = tlb_balance[exit_p - 1] + rcf_balance[exit_p - 1]
        exit_cash = cash_balance[exit_p - 1]
        equity_value_before_floor = exit_ev - exit_fees - exit_debt + exit_cash
        equity_proceeds = max(equity_value_before_floor, 0.0)
        
        pref_pik = inputs['preferred_pik_rate']
        preferred_accrued = preferred_equity * ((1.0 + pref_pik) ** holding_period_years)
        
        if equity_proceeds - preferred_accrued <= 1e-12 * equity_proceeds:
            preferred_payout = equity_proceeds
        else:
            preferred_payout = preferred_accrued
        ordinary_payout = equity_proceeds - preferred_payout
        
        mgmt_ord_frac = inputs['management_ordinary_fraction']
        sponsor_proceeds = preferred_payout + ordinary_payout * (1.0 - mgmt_ord_frac)
        management_proceeds = ordinary_payout * mgmt_ord_frac
        
        deal_mom = (equity_proceeds / entry_equity) if entry_equity > 0 else None
        sponsor_mom = (sponsor_proceeds / sponsor_investment) if sponsor_investment > 0 else None
        management_mom = (management_proceeds / management_investment) if management_investment > 0 else None
        
        deal_irr = ((equity_proceeds / entry_equity) ** (1.0 / holding_period_years) - 1.0) if (entry_equity > 0 and equity_proceeds > 0) else None
        sponsor_irr = ((sponsor_proceeds / sponsor_investment) ** (1.0 / holding_period_years) - 1.0) if (sponsor_investment > 0 and sponsor_proceeds > 0) else None
        management_irr = ((management_proceeds / management_investment) ** (1.0 / holding_period_years) - 1.0) if (management_investment > 0 and management_proceeds > 0) else None
    else:
        exit_ev = None
        exit_fees = None
        exit_debt = None
        exit_cash = None
        equity_value_before_floor = None
        equity_proceeds = None
        preferred_accrued = None
        preferred_payout = None
        ordinary_payout = None
        sponsor_proceeds = None
        management_proceeds = None
        deal_mom = None
        sponsor_mom = None
        management_mom = None
        deal_irr = None
        sponsor_irr = None
        management_irr = None

    return {
        "status": status,
        "failure_period": failure_period,
        "funding_shortfall": funding_shortfall,
        "dates": dates,
        "operating_fractions": operating_fractions,
        "interest_year_fractions": interest_year_fractions,
        "exit_date": exit_date,
        "holding_period_years": holding_period_years,
        "entry_ebitda": entry_ebitda,
        "entry_ev": entry_ev,
        "entry_equity": entry_equity,
        "ordinary_equity": ordinary_equity,
        "preferred_equity": preferred_equity,
        "sponsor_investment": sponsor_investment,
        "management_investment": management_investment,
        "revenue": revenue,
        "gross_profit": gross_profit,
        "opex": opex,
        "ebitda": ebitda,
        "ebitda_margin": ebitda_margin,
        "working_capital": working_capital,
        "change_working_capital": change_working_capital,
        "cash_capex": cash_capex,
        "cash_ebitda": cash_ebitda,
        "cash_interest": cash_interest,
        "tlb_interest": tlb_interest,
        "rcf_interest": rcf_interest,
        "cash_taxes": cash_taxes,
        "pre_financing_cash_flow": pre_financing_cash_flow,
        "tlb_pik": tlb_pik,
        "mandatory_tlb_repayment": mandatory_tlb_repayment,
        "mandatory_rcf_repayment": mandatory_rcf_repayment,
        "rcf_draw": rcf_draw,
        "rcf_repayment": rcf_repayment,
        "tlb_sweep": tlb_sweep,
        "tlb_balance": tlb_balance,
        "rcf_balance": rcf_balance,
        "cash_balance": cash_balance,
        "exit_ev": exit_ev,
        "exit_fees": exit_fees,
        "exit_debt": exit_debt,
        "exit_cash": exit_cash,
        "equity_value_before_floor": equity_value_before_floor,
        "equity_proceeds": equity_proceeds,
        "preferred_accrued": preferred_accrued,
        "preferred_payout": preferred_payout,
        "ordinary_payout": ordinary_payout,
        "sponsor_proceeds": sponsor_proceeds,
        "management_proceeds": management_proceeds,
        "deal_mom": deal_mom,
        "sponsor_mom": sponsor_mom,
        "management_mom": management_mom,
        "deal_irr": deal_irr,
        "sponsor_irr": sponsor_irr,
        "management_irr": management_irr,
    }

with open('inputs/base_case.json') as f:
    inp = json.load(f)

res = solve(inp)
print(f"Total fields returned: {len(res)}")
