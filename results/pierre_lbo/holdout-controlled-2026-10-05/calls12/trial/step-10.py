import json, openpyxl

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=True)
ws_ret = wb['Returns']
ws_fc = wb['Forecast']
ws_debt = wb['Debt']

with open('inputs/base_case.json') as f:
    base_case = json.load(f)

# Let's import run_model from previous snippet
import calendar, datetime

def edate(dt, months):
    year = dt.year + (dt.month + months - 1) // 12
    month = (dt.month + months - 1) % 12 + 1
    max_days = calendar.monthrange(year, month)[1]
    day = min(dt.day, max_days)
    return datetime.date(year, month, day)

def run_model(data):
    case = data['case']
    last_fye = datetime.date.fromisoformat(data['last_fiscal_year_end'])
    deal_date = datetime.date.fromisoformat(data['deal_date'])
    exit_period = data['exit_period']
    opening_rev = data['opening_revenue']
    opening_wc = data['opening_working_capital']
    entry_mult = data['entry_multiple']
    exit_mult = data['exit_multiple']
    exit_fee_rate = data['exit_fee_rate']
    tax_rate = data['tax_rate']
    ord_eq_frac = data['ordinary_equity_fraction']
    mgmt_ord_frac = data['management_ordinary_fraction']
    pref_pik_rate = data['preferred_pik_rate']
    wc_ratios = data['working_capital_ratio']
    tlb_info = data['term_loan']
    rcf_info = data['revolver']
    scen = data['scenarios'][case - 1]

    rev_growth = scen['revenue_growth']
    gp_margin = scen['gross_profit_margin']
    op_margin = scen['opex_margin']
    scen_capex = scen['capex']

    dates = []
    operating_fractions = []
    interest_year_fractions = []

    curr_fye = last_fye
    for t in range(1, exit_period + 1):
        next_fye = edate(curr_fye, 12)
        dates.append(next_fye.isoformat())
        if t == 1:
            cf_start = deal_date
            op_frac = (next_fye - deal_date).days / (next_fye - last_fye).days
        else:
            cf_start = curr_fye
            op_frac = 1.0
        int_frac = (next_fye - cf_start).days / 365.0
        operating_fractions.append(op_frac)
        interest_year_fractions.append(int_frac)
        curr_fye = next_fye

    exit_date = dates[exit_period - 1]
    holding_period_years = (curr_fye - deal_date).days / 365.0

    revenue = []
    gross_profit = []
    opex = []
    ebitda = []
    ebitda_margin = []
    working_capital = []
    change_working_capital = []
    cash_capex = []
    cash_ebitda = []

    prev_rev = opening_rev
    prev_wc = opening_wc
    for t in range(exit_period):
        rev = prev_rev * (1.0 + rev_growth[t])
        gp = rev * gp_margin[t]
        op = rev * op_margin[t]
        eb = gp - op
        eb_m = gp_margin[t] - op_margin[t]
        wc = rev * wc_ratios[t]
        ch_wc = wc - prev_wc
        c_cap = scen_capex[t] * operating_fractions[t]
        c_eb = eb * operating_fractions[t]

        revenue.append(rev)
        gross_profit.append(gp)
        opex.append(op)
        ebitda.append(eb)
        ebitda_margin.append(eb_m)
        working_capital.append(wc)
        change_working_capital.append(ch_wc)
        cash_capex.append(c_cap)
        cash_ebitda.append(c_eb)

        prev_rev = rev
        prev_wc = wc

    entry_ebitda = ebitda[0]
    entry_ev = entry_ebitda * entry_mult
    entry_equity = entry_ev - tlb_info['principal']
    ordinary_equity = entry_equity * ord_eq_frac
    preferred_equity = entry_equity - ordinary_equity
    management_investment = ordinary_equity * mgmt_ord_frac
    sponsor_investment = entry_equity - management_investment

    status = "ok"
    failure_period = None
    funding_shortfall = 0

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

    tlb_bal = tlb_info['principal']
    rcf_bal = 0.0
    cash_bal = 0.0

    for t in range(1, exit_period + 1):
        idx = t - 1
        open_tlb = tlb_bal
        open_rcf = rcf_bal
        open_cash = cash_bal

        tlb_int = open_tlb * tlb_info['cash_rate'] * interest_year_fractions[idx]
        rcf_int = open_rcf * rcf_info['cash_rate'] * interest_year_fractions[idx]
        c_int = tlb_int + rcf_int
        tlb_p = open_tlb * tlb_info['pik_rate'] * interest_year_fractions[idx]
        c_tax = max(cash_ebitda[idx] - c_int, 0.0) * tax_rate
        pfc = cash_ebitda[idx] - cash_capex[idx] - change_working_capital[idx] - c_tax

        if t >= tlb_info['maturity_period']:
            mand_tlb = open_tlb + tlb_p
        else:
            mand_tlb = min(open_tlb + tlb_p, tlb_info['principal'] * tlb_info['amortization_rate'] * operating_fractions[idx])

        if t >= rcf_info['maturity_period']:
            mand_rcf = open_rcf
        else:
            mand_rcf = 0.0

        cash_before_rep = open_cash + pfc - c_int
        req_draw = max(mand_tlb + mand_rcf - cash_before_rep, 0.0)

        if t < rcf_info['maturity_period']:
            avail_draw = max(rcf_info['commitment'] - open_rcf, 0.0)
        else:
            avail_draw = 0.0

        shortfall = max(req_draw - avail_draw, 0.0)
        scale = max(open_cash, abs(cash_ebitda[idx]), cash_capex[idx], abs(change_working_capital[idx]),
                    c_tax, c_int, mand_tlb + mand_rcf, avail_draw)

        if shortfall > 1e-12 * scale:
            status = "liquidity_shortfall"
            failure_period = t
            funding_shortfall = shortfall
            break

        draw = min(req_draw, avail_draw)
        cash_after_mand = max(cash_before_rep + draw - mand_tlb - mand_rcf, 0.0)
        interim_rcf = open_rcf + draw - mand_rcf
        vol_rcf = min(cash_after_mand, interim_rcf)
        tot_rcf_rep = mand_rcf + vol_rcf
        cash_after_rcf = cash_after_mand - vol_rcf

        sweep = min(cash_after_rcf * tlb_info['cash_sweep'], open_tlb + tlb_p - mand_tlb)
        tlb_bal = open_tlb + tlb_p - mand_tlb - sweep
        rcf_bal = interim_rcf - vol_rcf
        cash_bal = cash_after_rcf - sweep

        cash_interest.append(c_int)
        tlb_interest.append(tlb_int)
        rcf_interest.append(rcf_int)
        cash_taxes.append(c_tax)
        pre_financing_cash_flow.append(pfc)
        tlb_pik.append(tlb_p)
        mandatory_tlb_repayment.append(mand_tlb)
        mandatory_rcf_repayment.append(mand_rcf)
        rcf_draw.append(draw)
        rcf_repayment.append(tot_rcf_rep)
        tlb_sweep.append(sweep)
        tlb_balance.append(tlb_bal)
        rcf_balance.append(rcf_bal)
        cash_balance.append(cash_bal)

    if status == "ok":
        exit_ev = ebitda[exit_period - 1] * exit_mult
        exit_fees = max(exit_ev, 0.0) * exit_fee_rate
        exit_debt = tlb_balance[-1] + rcf_balance[-1]
        exit_cash = cash_balance[-1]
        equity_value_before_floor = exit_ev - exit_fees - exit_debt + exit_cash
        equity_proceeds = max(equity_value_before_floor, 0.0)

        preferred_accrued = preferred_equity * ((1.0 + pref_pik_rate) ** holding_period_years)
        if equity_proceeds - preferred_accrued <= 1e-12 * equity_proceeds:
            preferred_payout = equity_proceeds
            ordinary_payout = 0.0
        else:
            preferred_payout = preferred_accrued
            ordinary_payout = equity_proceeds - preferred_accrued

        sponsor_proceeds = preferred_payout + ordinary_payout * (1.0 - mgmt_ord_frac)
        management_proceeds = ordinary_payout * mgmt_ord_frac

        deal_mom = equity_proceeds / entry_equity if entry_equity > 0 else None
        sponsor_mom = sponsor_proceeds / sponsor_investment if sponsor_investment > 0 else None
        management_mom = management_proceeds / management_investment if management_investment > 0 else None

        deal_irr = (equity_proceeds / entry_equity) ** (1.0 / holding_period_years) - 1.0 if (entry_equity > 0 and equity_proceeds > 0) else None
        sponsor_irr = (sponsor_proceeds / sponsor_investment) ** (1.0 / holding_period_years) - 1.0 if (sponsor_investment > 0 and sponsor_proceeds > 0) else None
        management_irr = (management_proceeds / management_investment) ** (1.0 / holding_period_years) - 1.0 if (management_investment > 0 and management_proceeds > 0) else None
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

    result = {
        'status': status,
        'failure_period': failure_period,
        'funding_shortfall': funding_shortfall,
        'dates': dates,
        'operating_fractions': operating_fractions,
        'interest_year_fractions': interest_year_fractions,
        'exit_date': exit_date,
        'holding_period_years': holding_period_years,
        'entry_ebitda': entry_ebitda,
        'entry_ev': entry_ev,
        'entry_equity': entry_equity,
        'ordinary_equity': ordinary_equity,
        'preferred_equity': preferred_equity,
        'sponsor_investment': sponsor_investment,
        'management_investment': management_investment,
        'revenue': revenue,
        'gross_profit': gross_profit,
        'opex': opex,
        'ebitda': ebitda,
        'ebitda_margin': ebitda_margin,
        'working_capital': working_capital,
        'change_working_capital': change_working_capital,
        'cash_capex': cash_capex,
        'cash_ebitda': cash_ebitda,
        'cash_interest': cash_interest,
        'tlb_interest': tlb_interest,
        'rcf_interest': rcf_interest,
        'cash_taxes': cash_taxes,
        'pre_financing_cash_flow': pre_financing_cash_flow,
        'tlb_pik': tlb_pik,
        'mandatory_tlb_repayment': mandatory_tlb_repayment,
        'mandatory_rcf_repayment': mandatory_rcf_repayment,
        'rcf_draw': rcf_draw,
        'rcf_repayment': rcf_repayment,
        'tlb_sweep': tlb_sweep,
        'tlb_balance': tlb_balance,
        'rcf_balance': rcf_balance,
        'cash_balance': cash_balance,
        'exit_ev': exit_ev,
        'exit_fees': exit_fees,
        'exit_debt': exit_debt,
        'exit_cash': exit_cash,
        'equity_value_before_floor': equity_value_before_floor,
        'equity_proceeds': equity_proceeds,
        'preferred_accrued': preferred_accrued,
        'preferred_payout': preferred_payout,
        'ordinary_payout': ordinary_payout,
        'sponsor_proceeds': sponsor_proceeds,
        'management_proceeds': management_proceeds,
        'deal_mom': deal_mom,
        'sponsor_mom': sponsor_mom,
        'management_mom': management_mom,
        'deal_irr': deal_irr,
        'sponsor_irr': sponsor_irr,
        'management_irr': management_irr,
    }
    return result

res = run_model(base_case)

# Compare with Returns sheet
ret_rows = {
    'entry_ebitda': 5, 'entry_ev': 6, 'entry_equity': 7, 'ordinary_equity': 8, 'preferred_equity': 9,
    'sponsor_investment': 10, 'management_investment': 11, 'exit_date': 13, 'holding_period_years': 14,
    'status': 16, 'failure_period': 17, 'funding_shortfall': 18, 'exit_ev': 20, 'exit_fees': 21,
    'exit_debt': 22, 'exit_cash': 23, 'equity_value_before_floor': 24, 'equity_proceeds': 25,
    'preferred_accrued': 27, 'preferred_payout': 28, 'ordinary_payout': 29, 'sponsor_proceeds': 30,
    'management_proceeds': 31, 'deal_mom': 33, 'sponsor_mom': 34, 'management_mom': 35,
    'deal_irr': 37, 'sponsor_irr': 38, 'management_irr': 39
}

diffs = 0
for k, r in ret_rows.items():
    wb_val = ws_ret.cell(r, 2).value
    my_val = res[k]
    if isinstance(wb_val, datetime.datetime):
        wb_val = wb_val.strftime('%Y-%m-%d')
    if wb_val is None or wb_val == "":
        wb_val = None
    if isinstance(wb_val, (int, float)) and isinstance(my_val, (int, float)):
        diff = abs(wb_val - my_val)
        if diff > 1e-6:
            print(f"Mismatch in {k}: wb={wb_val}, my={my_val}")
            diffs += 1
    else:
        if wb_val != my_val:
            print(f"Mismatch in {k}: wb={wb_val}, my={my_val}")
            diffs += 1

print(f"Returns comparisons complete. Differences found: {diffs}")
