import sys
import json
import datetime
import calendar

def edate(dt: datetime.date, months: int) -> datetime.date:
    y = dt.year + (dt.month + months - 1) // 12
    m = (dt.month + months - 1) % 12 + 1
    max_d = calendar.monthrange(y, m)[1]
    d = min(dt.day, max_d)
    return datetime.date(y, m, d)

def run_model(inp):
    case_idx = inp["case"] - 1
    scenarios = inp["scenarios"][case_idx]
    exit_period = inp["exit_period"]
    last_fiscal_end = datetime.date.fromisoformat(inp["last_fiscal_year_end"])
    deal_date = datetime.date.fromisoformat(inp["deal_date"])

    dates = []
    operating_fractions = []
    interest_year_fractions = []

    prev_fiscal = last_fiscal_end
    for p in range(1, exit_period + 1):
        f_end = edate(prev_fiscal, 12)
        dates.append(f_end.isoformat())
        start_date = max(prev_fiscal, deal_date)
        op_frac = (f_end - start_date).days / (f_end - prev_fiscal).days
        int_frac = (f_end - start_date).days / 365.0
        operating_fractions.append(op_frac)
        interest_year_fractions.append(int_frac)
        prev_fiscal = f_end

    exit_date = dates[exit_period - 1]
    exit_date_dt = datetime.date.fromisoformat(exit_date)
    holding_period_years = (exit_date_dt - deal_date).days / 365.0

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

    cur_rev = float(inp["opening_revenue"])
    prev_wc = float(inp["opening_working_capital"])

    for p in range(1, exit_period + 1):
        idx = p - 1
        growth = scenarios["revenue_growth"][idx]
        gp_m = scenarios["gross_profit_margin"][idx]
        op_m = scenarios["opex_margin"][idx]
        cap = scenarios["capex"][idx]
        wc_r = inp["working_capital_ratio"][idx]

        cur_rev = cur_rev * (1.0 + growth)
        revenue.append(cur_rev)
        gp = cur_rev * gp_m
        gross_profit.append(gp)
        op = cur_rev * op_m
        opex.append(op)
        eb = gp - op
        ebitda.append(eb)
        ebitda_margin.append(gp_m - op_m)
        wc = cur_rev * wc_r
        working_capital.append(wc)
        change_working_capital.append(wc - prev_wc)
        prev_wc = wc

        cash_capex.append(cap * operating_fractions[idx])
        cash_ebitda.append(eb * operating_fractions[idx])

    # Initial funding
    entry_ebitda = ebitda[0]
    entry_ev = entry_ebitda * inp["entry_multiple"]
    tlb_orig_principal = float(inp["term_loan"]["principal"])
    entry_equity = entry_ev - tlb_orig_principal
    ordinary_equity = entry_equity * inp["ordinary_equity_fraction"]
    preferred_equity = entry_equity - ordinary_equity
    management_investment = ordinary_equity * inp["management_ordinary_fraction"]
    sponsor_investment = entry_equity - management_investment

    # Debt financing
    cash_interest_arr = []
    tlb_interest_arr = []
    rcf_interest_arr = []
    cash_taxes_arr = []
    pre_financing_cash_flow_arr = []
    tlb_pik_arr = []
    mandatory_tlb_repayment_arr = []
    mandatory_rcf_repayment_arr = []
    rcf_draw_arr = []
    rcf_repayment_arr = []
    tlb_sweep_arr = []
    tlb_balance_arr = []
    rcf_balance_arr = []
    cash_balance_arr = []

    status = "ok"
    failure_period = None
    funding_shortfall = 0.0

    cur_tlb = tlb_orig_principal
    cur_rcf = 0.0
    cur_cash = 0.0

    tl_cfg = inp["term_loan"]
    rcf_cfg = inp["revolver"]

    for p in range(1, exit_period + 1):
        idx = p - 1
        int_frac = interest_year_fractions[idx]
        op_frac = operating_fractions[idx]

        tlb_interest = cur_tlb * tl_cfg["cash_rate"] * int_frac
        rcf_interest = cur_rcf * rcf_cfg["cash_rate"] * int_frac
        cash_interest = tlb_interest + rcf_interest
        tlb_pik = cur_tlb * tl_cfg["pik_rate"] * int_frac

        c_eb = cash_ebitda[idx]
        cash_taxes = max(c_eb - cash_interest, 0.0) * inp["tax_rate"]
        pref_cf = c_eb - cash_capex[idx] - change_working_capital[idx] - cash_taxes

        # mandatory TLB
        if p >= tl_cfg["maturity_period"]:
            prop_mand_tlb = cur_tlb + tlb_pik
        else:
            prop_mand_tlb = min(cur_tlb + tlb_pik, tlb_orig_principal * tl_cfg["amortization_rate"] * op_frac)

        # mandatory RCF
        if p >= rcf_cfg["maturity_period"]:
            prop_mand_rcf = cur_rcf
        else:
            prop_mand_rcf = 0.0

        cash_before_rep = cur_cash + pref_cf - cash_interest
        req_draw = max(prop_mand_tlb + prop_mand_rcf - cash_before_rep, 0.0)

        if p < rcf_cfg["maturity_period"]:
            avail_draw = max(rcf_cfg["commitment"] - cur_rcf, 0.0)
        else:
            avail_draw = 0.0

        pot_shortfall = max(req_draw - avail_draw, 0.0)
        liq_scale = max(
            cur_cash,
            abs(c_eb),
            cash_capex[idx],
            abs(change_working_capital[idx]),
            cash_taxes,
            cash_interest,
            prop_mand_tlb + prop_mand_rcf,
            avail_draw
        )

        if pot_shortfall > 1e-12 * liq_scale:
            status = "liquidity_shortfall"
            failure_period = p
            funding_shortfall = pot_shortfall
            break

        # Financed row
        rcf_draw = min(req_draw, avail_draw)
        mand_tlb = prop_mand_tlb
        mand_rcf = prop_mand_rcf

        cash_after_mand = max(cash_before_rep + rcf_draw - mand_tlb - mand_rcf, 0.0)
        interim_rcf = cur_rcf + rcf_draw - mand_rcf
        vol_rcf_rep = min(cash_after_mand, interim_rcf)
        tot_rcf_rep = mand_rcf + vol_rcf_rep
        cash_after_rcf = cash_after_mand - vol_rcf_rep

        tlb_sweep = min(cash_after_rcf * tl_cfg["cash_sweep"], cur_tlb + tlb_pik - mand_tlb)
        next_tlb = cur_tlb + tlb_pik - mand_tlb - tlb_sweep
        next_rcf = interim_rcf - vol_rcf_rep
        next_cash = cash_after_rcf - tlb_sweep

        cash_interest_arr.append(cash_interest)
        tlb_interest_arr.append(tlb_interest)
        rcf_interest_arr.append(rcf_interest)
        cash_taxes_arr.append(cash_taxes)
        pre_financing_cash_flow_arr.append(pref_cf)
        tlb_pik_arr.append(tlb_pik)
        mandatory_tlb_repayment_arr.append(mand_tlb)
        mandatory_rcf_repayment_arr.append(mand_rcf)
        rcf_draw_arr.append(rcf_draw)
        rcf_repayment_arr.append(tot_rcf_rep)
        tlb_sweep_arr.append(tlb_sweep)
        tlb_balance_arr.append(next_tlb)
        rcf_balance_arr.append(next_rcf)
        cash_balance_arr.append(next_cash)

        cur_tlb = next_tlb
        cur_rcf = next_rcf
        cur_cash = next_cash

    # Exit bridge & waterfall
    if status == "ok":
        exit_ev = ebitda[exit_period - 1] * inp["exit_multiple"]
        exit_fees = max(exit_ev, 0.0) * inp["exit_fee_rate"]
        exit_debt = tlb_balance_arr[-1] + rcf_balance_arr[-1]
        exit_cash = cash_balance_arr[-1]
        equity_value_before_floor = exit_ev - exit_fees - exit_debt + exit_cash
        equity_proceeds = max(equity_value_before_floor, 0.0)

        pref_accrued = preferred_equity * ((1.0 + inp["preferred_pik_rate"]) ** holding_period_years)
        if equity_proceeds - pref_accrued <= 1e-12 * equity_proceeds:
            pref_payout = equity_proceeds
        else:
            pref_payout = pref_accrued
        ord_payout = equity_proceeds - pref_payout
        sponsor_proceeds = pref_payout + ord_payout * (1.0 - inp["management_ordinary_fraction"])
        mgmt_proceeds = ord_payout * inp["management_ordinary_fraction"]

        deal_mom = equity_proceeds / entry_equity if entry_equity > 0 else None
        sponsor_mom = sponsor_proceeds / sponsor_investment if sponsor_investment > 0 else None
        mgmt_mom = mgmt_proceeds / management_investment if management_investment > 0 else None

        deal_irr = (deal_mom ** (1.0 / holding_period_years) - 1.0) if (entry_equity > 0 and equity_proceeds > 0) else None
        sponsor_irr = (sponsor_mom ** (1.0 / holding_period_years) - 1.0) if (sponsor_investment > 0 and sponsor_proceeds > 0) else None
        mgmt_irr = (mgmt_mom ** (1.0 / holding_period_years) - 1.0) if (management_investment > 0 and mgmt_proceeds > 0) else None
    else:
        exit_ev = None
        exit_fees = None
        exit_debt = None
        exit_cash = None
        equity_value_before_floor = None
        equity_proceeds = None
        pref_accrued = None
        pref_payout = None
        ord_payout = None
        sponsor_proceeds = None
        mgmt_proceeds = None
        deal_mom = None
        sponsor_mom = None
        mgmt_mom = None
        deal_irr = None
        sponsor_irr = None
        mgmt_irr = None

    result = {
        # Status and timing
        "status": status,
        "failure_period": failure_period,
        "funding_shortfall": funding_shortfall,
        "dates": dates,
        "operating_fractions": operating_fractions,
        "interest_year_fractions": interest_year_fractions,
        "exit_date": exit_date,
        "holding_period_years": holding_period_years,
        # Initial funding
        "entry_ebitda": entry_ebitda,
        "entry_ev": entry_ev,
        "entry_equity": entry_equity,
        "ordinary_equity": ordinary_equity,
        "preferred_equity": preferred_equity,
        "sponsor_investment": sponsor_investment,
        "management_investment": management_investment,
        # Forecast arrays
        "revenue": revenue,
        "gross_profit": gross_profit,
        "opex": opex,
        "ebitda": ebitda,
        "ebitda_margin": ebitda_margin,
        "working_capital": working_capital,
        "change_working_capital": change_working_capital,
        "cash_capex": cash_capex,
        "cash_ebitda": cash_ebitda,
        # Financing arrays
        "cash_interest": cash_interest_arr,
        "tlb_interest": tlb_interest_arr,
        "rcf_interest": rcf_interest_arr,
        "cash_taxes": cash_taxes_arr,
        "pre_financing_cash_flow": pre_financing_cash_flow_arr,
        "tlb_pik": tlb_pik_arr,
        "mandatory_tlb_repayment": mandatory_tlb_repayment_arr,
        "mandatory_rcf_repayment": mandatory_rcf_repayment_arr,
        "rcf_draw": rcf_draw_arr,
        "rcf_repayment": rcf_repayment_arr,
        "tlb_sweep": tlb_sweep_arr,
        "tlb_balance": tlb_balance_arr,
        "rcf_balance": rcf_balance_arr,
        "cash_balance": cash_balance_arr,
        # Exit bridge
        "exit_ev": exit_ev,
        "exit_fees": exit_fees,
        "exit_debt": exit_debt,
        "exit_cash": exit_cash,
        "equity_value_before_floor": equity_value_before_floor,
        "equity_proceeds": equity_proceeds,
        # Waterfall and returns
        "preferred_accrued": preferred_accrued,
        "preferred_payout": pref_payout,
        "ordinary_payout": ord_payout,
        "sponsor_proceeds": sponsor_proceeds,
        "management_proceeds": mgmt_proceeds,
        "deal_mom": deal_mom,
        "sponsor_mom": sponsor_mom,
        "management_mom": mgmt_mom,
        "deal_irr": deal_irr,
        "sponsor_irr": sponsor_irr,
        "management_irr": mgmt_irr,
    }
    return result

def main():
    inp = json.load(sys.stdin)
    out = run_model(inp)
    json.dump(out, sys.stdout, indent=2)

if __name__ == "__main__":
    main()
