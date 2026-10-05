"""Pierre LBO One: standalone annual operating model and cash-funded waterfall."""
import calendar
from datetime import date
import json
import math
import sys
FORECAST_FIELDS = ('revenue', 'gross_profit', 'opex', 'ebitda', 'ebitda_margin', 'working_capital', 'change_working_capital', 'cash_capex', 'cash_ebitda')
FINANCING_FIELDS = ('cash_interest', 'tlb_interest', 'rcf_interest', 'cash_taxes', 'pre_financing_cash_flow', 'tlb_pik', 'mandatory_tlb_repayment', 'mandatory_rcf_repayment', 'rcf_draw', 'rcf_repayment', 'tlb_sweep', 'tlb_balance', 'rcf_balance', 'cash_balance')
EXIT_FIELDS = ('exit_ev', 'exit_fees', 'exit_debt', 'exit_cash', 'equity_value_before_floor', 'equity_proceeds', 'preferred_accrued', 'preferred_payout', 'ordinary_payout', 'sponsor_proceeds', 'management_proceeds', 'deal_mom', 'sponsor_mom', 'management_mom', 'deal_irr', 'sponsor_irr', 'management_irr')
INPUT_FIELDS = {'case', 'last_fiscal_year_end', 'deal_date', 'exit_period', 'opening_revenue', 'opening_working_capital', 'entry_multiple', 'exit_multiple', 'exit_fee_rate', 'tax_rate', 'ordinary_equity_fraction', 'management_ordinary_fraction', 'preferred_pik_rate', 'working_capital_ratio', 'term_loan', 'revolver', 'scenarios'}

def _number(value, name, minimum=0, maximum=None, strict=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite number')
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < minimum or (strict and value == minimum):
        raise ValueError(f'{name} is outside its numeric domain')
    if maximum is not None and value > maximum:
        raise ValueError(f'{name} exceeds {maximum}')

def _integer(value, name, minimum, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} must be an integer')
    _number(value, name, minimum, maximum)

def _mapping(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{name} has invalid keys')

def _vector(value, name, minimum=0, maximum=None, strict=False):
    if not isinstance(value, list) or len(value) != 8:
        raise ValueError(f'{name} must contain eight values')
    for item in value:
        _number(item, name, minimum, maximum, strict)

def _iso_date(value, name):
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f'{name} must be an ISO calendar date') from None
    if parsed.isoformat() != value:
        raise ValueError(f'{name} must use YYYY-MM-DD')
    return parsed

def _next_year(value):
    year = value.year + 1
    try:
        return date(year, value.month, min(value.day, calendar.monthrange(year, value.month)[1]))
    except ValueError:
        raise ValueError('forecast dates exceed the supported calendar') from None

def _validate(inputs):
    _mapping(inputs, INPUT_FIELDS, 'inputs')
    _integer(inputs['case'], 'case', 1, 4)
    _integer(inputs['exit_period'], 'exit_period', 1, 8)
    _number(inputs['opening_revenue'], 'opening_revenue', strict=True)
    for key in ('opening_working_capital', 'entry_multiple', 'exit_multiple', 'preferred_pik_rate'):
        _number(inputs[key], key)
    for key in ('exit_fee_rate', 'tax_rate', 'ordinary_equity_fraction', 'management_ordinary_fraction'):
        _number(inputs[key], key, maximum=1)
    _vector(inputs['working_capital_ratio'], 'working_capital_ratio')
    tlb, rcf = (inputs['term_loan'], inputs['revolver'])
    _mapping(tlb, ('principal', 'cash_rate', 'pik_rate', 'amortization_rate', 'cash_sweep', 'maturity_period'), 'term_loan')
    _mapping(rcf, ('commitment', 'cash_rate', 'maturity_period'), 'revolver')
    for key in ('principal', 'cash_rate', 'pik_rate'):
        _number(tlb[key], f'term_loan.{key}')
    for key in ('amortization_rate', 'cash_sweep'):
        _number(tlb[key], f'term_loan.{key}', maximum=1)
    _integer(tlb['maturity_period'], 'term_loan.maturity_period', 1)
    for key in ('commitment', 'cash_rate'):
        _number(rcf[key], f'revolver.{key}')
    _integer(rcf['maturity_period'], 'revolver.maturity_period', 1)
    scenarios = inputs['scenarios']
    if not isinstance(scenarios, list) or len(scenarios) != 4:
        raise ValueError('scenarios must contain four profiles')
    for scenario in scenarios:
        _mapping(scenario, ('revenue_growth', 'gross_profit_margin', 'opex_margin', 'capex'), 'scenario')
        _vector(scenario['revenue_growth'], 'revenue_growth', -1, strict=True)
        _vector(scenario['gross_profit_margin'], 'gross_profit_margin', maximum=1)
        _vector(scenario['opex_margin'], 'opex_margin', maximum=1)
        _vector(scenario['capex'], 'capex')
    previous = _iso_date(inputs['last_fiscal_year_end'], 'last_fiscal_year_end')
    closing = _iso_date(inputs['deal_date'], 'deal_date')
    if not previous < closing < _next_year(previous):
        raise ValueError('deal_date must lie strictly inside the first fiscal period')
    return (previous, closing)

def value_lbo(inputs: dict) -> dict:
    """Return 55 flat output fields; infeasible financing retains only completed rows.

    Cash tax excludes PIK, D&A and loss carryforwards. Annual valuations are not
    stubbed; cash EBITDA/capex are stubbed, but working-capital movements are not.
    """
    previous, closing = _validate(inputs)
    scenario = inputs['scenarios'][inputs['case'] - 1]
    tlb, rcf = (inputs['term_loan'], inputs['revolver'])
    out = {'status': 'ok', 'failure_period': None, 'funding_shortfall': 0.0, 'dates': [], 'operating_fractions': [], 'interest_year_fractions': []}
    out.update({key: [] for key in FORECAST_FIELDS + FINANCING_FIELDS})
    out.update({key: None for key in EXIT_FIELDS})
    revenue, wc = (inputs['opening_revenue'], inputs['opening_working_capital'])
    for index in range(inputs['exit_period']):
        end = _next_year(previous)
        days = (end - max(previous, closing)).days
        fraction = days / (end - previous).days
        out['dates'].append(end.isoformat())
        out['operating_fractions'].append(fraction)
        out['interest_year_fractions'].append(days / 365)
        revenue *= 1 + scenario['revenue_growth'][index]
        gp = revenue * scenario['gross_profit_margin'][index]
        opex = revenue * scenario['opex_margin'][index]
        next_wc = revenue * inputs['working_capital_ratio'][index]
        values = (revenue, gp, opex, gp - opex, scenario['gross_profit_margin'][index] - scenario['opex_margin'][index], next_wc, next_wc - wc, scenario['capex'][index] * fraction, (gp - opex) * fraction)
        for key, value in zip(FORECAST_FIELDS, values):
            out[key].append(value)
        previous, wc = (end, next_wc)
    out['exit_date'] = out['dates'][-1]
    out['holding_period_years'] = (previous - closing).days / 365
    out['entry_ebitda'] = out['ebitda'][0]
    out['entry_ev'] = out['entry_ebitda'] * inputs['entry_multiple']
    out['entry_equity'] = out['entry_ev'] - tlb['principal']
    if not math.isfinite(out['entry_equity']) or out['entry_equity'] <= 0:
        raise ValueError('derived entry_equity must be finite and strictly positive')
    out['ordinary_equity'] = out['entry_equity'] * inputs['ordinary_equity_fraction']
    out['preferred_equity'] = out['entry_equity'] - out['ordinary_equity']
    out['management_investment'] = out['ordinary_equity'] * inputs['management_ordinary_fraction']
    out['sponsor_investment'] = out['entry_equity'] - out['management_investment']
    debt, revolver, cash = (tlb['principal'], 0.0, 0.0)
    for index in range(inputs['exit_period']):
        period = index + 1
        years = out['interest_year_fractions'][index]
        tlb_interest = 0.0
        rcf_interest = 0.0
        interest = tlb_interest + rcf_interest
        pik = debt * tlb['pik_rate'] * years
        tax = max(out['cash_ebitda'][index] - interest, 0) * inputs['tax_rate']
        pre_financing = out['cash_ebitda'][index] - out['cash_capex'][index] - out['change_working_capital'][index] - tax
        mandatory_tlb = min(debt + pik, tlb['principal'] * tlb['amortization_rate'] * out['operating_fractions'][index])
        if period >= tlb['maturity_period']:
            mandatory_tlb = debt + pik
        mandatory_rcf = revolver if period >= rcf['maturity_period'] else 0.0
        before = cash + pre_financing - interest
        required = max(mandatory_tlb + mandatory_rcf - before, 0.0)
        available = max(rcf['commitment'] - revolver, 0.0) if period < rcf['maturity_period'] else 0.0
        liquidity_scale = max(cash, abs(out['cash_ebitda'][index]), out['cash_capex'][index], abs(out['change_working_capital'][index]), tax, interest, mandatory_tlb + mandatory_rcf, available)
        if required - available > 1e-12 * liquidity_scale:
            out.update(status='liquidity_shortfall', failure_period=period, funding_shortfall=required - available)
            return out
        draw = min(required, available)
        cash = max(before + draw - mandatory_tlb - mandatory_rcf, 0.0)
        revolver += draw - mandatory_rcf
        voluntary_rcf = min(cash, revolver)
        cash -= voluntary_rcf
        revolver -= voluntary_rcf
        debt = debt + pik - mandatory_tlb
        sweep = min(cash * tlb['cash_sweep'], debt)
        debt -= sweep
        cash -= sweep
        values = (interest, tlb_interest, rcf_interest, tax, pre_financing, pik, mandatory_tlb, mandatory_rcf, draw, mandatory_rcf + voluntary_rcf, sweep, debt, revolver, cash)
        for key, value in zip(FINANCING_FIELDS, values):
            out[key].append(value)
    out['exit_ev'] = out['ebitda'][-1] * inputs['exit_multiple']
    out['exit_fees'] = max(out['exit_ev'], 0) * inputs['exit_fee_rate']
    out['exit_debt'], out['exit_cash'] = (debt + revolver, cash)
    out['equity_value_before_floor'] = out['exit_ev'] - out['exit_fees'] - debt - revolver + cash
    out['equity_proceeds'] = max(out['equity_value_before_floor'], 0.0)
    out['preferred_accrued'] = out['preferred_equity'] * (1 + inputs['preferred_pik_rate']) ** out['holding_period_years']
    out['preferred_payout'] = out['equity_proceeds'] if out['equity_proceeds'] - out['preferred_accrued'] <= 1e-12 * out['equity_proceeds'] else out['preferred_accrued']
    out['ordinary_payout'] = out['equity_proceeds'] - out['preferred_payout']
    out['management_proceeds'] = out['ordinary_payout'] * inputs['management_ordinary_fraction']
    out['sponsor_proceeds'] = out['preferred_payout'] + out['ordinary_payout'] * (1 - inputs['management_ordinary_fraction'])
    for owner, investment, proceeds in (('deal', out['entry_equity'], out['equity_proceeds']), ('sponsor', out['sponsor_investment'], out['sponsor_proceeds']), ('management', out['management_investment'], out['management_proceeds'])):
        out[owner + '_mom'] = proceeds / investment if investment > 0 else None
        out[owner + '_irr'] = (proceeds / investment) ** (1 / out['holding_period_years']) - 1 if investment > 0 and proceeds > 0 else None
    return out
if __name__ == '__main__':
    json.dump(value_lbo(json.load(sys.stdin)), sys.stdout, allow_nan=False)
    sys.stdout.write('\n')
