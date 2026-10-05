# Compare forecast and financing arrays with the workbook
# Forecast columns:
# Period 1..5 in rows 5..9
# E: operating_fractions, F: interest_year_fractions, L: revenue, M: gross_profit, N: opex, O: ebitda, P: ebitda_margin, Q: working_capital, R: change_working_capital, S: cash_capex, T: cash_ebitda
# Debt columns:
# F: tlb_interest, G: rcf_interest, H: cash_interest, I: tlb_pik, J: cash_taxes, K: pre_financing_cash_flow, L: mandatory_tlb_repayment, M: mandatory_rcf_repayment, S: rcf_draw, W: rcf_repayment, Y: tlb_sweep, Z: tlb_balance, AA: rcf_balance, AB: cash_balance

fc_cols = {
    'operating_fractions': 'E', 'interest_year_fractions': 'F', 'revenue': 'L', 'gross_profit': 'M',
    'opex': 'N', 'ebitda': 'O', 'ebitda_margin': 'P', 'working_capital': 'Q', 'change_working_capital': 'R',
    'cash_capex': 'S', 'cash_ebitda': 'T'
}
debt_cols = {
    'tlb_interest': 'F', 'rcf_interest': 'G', 'cash_interest': 'H', 'tlb_pik': 'I', 'cash_taxes': 'J',
    'pre_financing_cash_flow': 'K', 'mandatory_tlb_repayment': 'L', 'mandatory_rcf_repayment': 'M',
    'rcf_draw': 'S', 'rcf_repayment': 'W', 'tlb_sweep': 'Y', 'tlb_balance': 'Z', 'rcf_balance': 'AA',
    'cash_balance': 'AB'
}

diffs = 0
for k, col in fc_cols.items():
    arr = res[k]
    for i in range(len(arr)):
        cell_val = ws_fc[f'{col}{5+i}'].value
        if abs(cell_val - arr[i]) > 1e-6:
            print(f"Mismatch in {k}[{i}]: wb={cell_val}, my={arr[i]}")
            diffs += 1

for k, col in debt_cols.items():
    arr = res[k]
    for i in range(len(arr)):
        cell_val = ws_debt[f'{col}{5+i}'].value
        if abs(cell_val - arr[i]) > 1e-6:
            print(f"Mismatch in {k}[{i}]: wb={cell_val}, my={arr[i]}")
            diffs += 1

print(f"Array comparisons complete. Differences found: {diffs}")
