import json, openpyxl, subprocess

with open('inputs/base_case.json') as f:
    inp_text = f.read()

res_proc = subprocess.run(['python3', 'solution.py'], input=inp_text, text=True, capture_output=True)
if res_proc.returncode != 0:
    print("Stderr:", res_proc.stderr)
res = json.loads(res_proc.stdout)

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=True)
forecast = wb['Forecast']
debt = wb['Debt']
returns = wb['Returns']
inputs = wb['Inputs']

exit_p = inputs['B8'].value

# Expected values from workbook:
expected = {}

# Forecast / timing
expected['dates'] = [forecast.cell(4+p, 3).value.strftime("%Y-%m-%d") for p in range(1, exit_p+1)]
expected['operating_fractions'] = [forecast.cell(4+p, 5).value for p in range(1, exit_p+1)]
expected['interest_year_fractions'] = [forecast.cell(4+p, 6).value for p in range(1, exit_p+1)]
expected['revenue'] = [forecast.cell(4+p, 12).value for p in range(1, exit_p+1)]
expected['gross_profit'] = [forecast.cell(4+p, 13).value for p in range(1, exit_p+1)]
expected['opex'] = [forecast.cell(4+p, 14).value for p in range(1, exit_p+1)]
expected['ebitda'] = [forecast.cell(4+p, 15).value for p in range(1, exit_p+1)]
expected['ebitda_margin'] = [forecast.cell(4+p, 16).value for p in range(1, exit_p+1)]
expected['working_capital'] = [forecast.cell(4+p, 17).value for p in range(1, exit_p+1)]
expected['change_working_capital'] = [forecast.cell(4+p, 18).value for p in range(1, exit_p+1)]
expected['cash_capex'] = [forecast.cell(4+p, 19).value for p in range(1, exit_p+1)]
expected['cash_ebitda'] = [forecast.cell(4+p, 20).value for p in range(1, exit_p+1)]

# Debt
expected['tlb_interest'] = [debt.cell(4+p, 6).value for p in range(1, exit_p+1)]
expected['rcf_interest'] = [debt.cell(4+p, 7).value for p in range(1, exit_p+1)]
expected['cash_interest'] = [debt.cell(4+p, 8).value for p in range(1, exit_p+1)]
expected['tlb_pik'] = [debt.cell(4+p, 9).value for p in range(1, exit_p+1)]
expected['cash_taxes'] = [debt.cell(4+p, 10).value for p in range(1, exit_p+1)]
expected['pre_financing_cash_flow'] = [debt.cell(4+p, 11).value for p in range(1, exit_p+1)]
expected['mandatory_tlb_repayment'] = [debt.cell(4+p, 12).value for p in range(1, exit_p+1)]
expected['mandatory_rcf_repayment'] = [debt.cell(4+p, 13).value for p in range(1, exit_p+1)]
expected['rcf_draw'] = [debt.cell(4+p, 19).value for p in range(1, exit_p+1)]
expected['rcf_repayment'] = [debt.cell(4+p, 23).value for p in range(1, exit_p+1)]
expected['tlb_sweep'] = [debt.cell(4+p, 25).value for p in range(1, exit_p+1)]
expected['tlb_balance'] = [debt.cell(4+p, 26).value for p in range(1, exit_p+1)]
expected['rcf_balance'] = [debt.cell(4+p, 27).value for p in range(1, exit_p+1)]
expected['cash_balance'] = [debt.cell(4+p, 28).value for p in range(1, exit_p+1)]

# Returns
for r in range(5, 40):
    k = returns.cell(r, 1).value
    v = returns.cell(r, 2).value
    if k:
        if isinstance(v, datetime):
            v = v.strftime("%Y-%m-%d")
        expected[k] = v

diffs = []
for k in res:
    if k not in expected:
        print(f"Key {k} not in expected!")
        continue
    exp_v = expected[k]
    act_v = res[k]
    
    if isinstance(act_v, list):
        if len(act_v) != len(exp_v):
            diffs.append(f"{k}: len {len(act_v)} != {len(exp_v)}")
        else:
            for i, (a, b) in enumerate(zip(act_v, exp_v)):
                if isinstance(a, str):
                    if a != b:
                        diffs.append(f"{k}[{i}]: {a} != {b}")
                else:
                    if abs(a - b) > 1e-7 * max(abs(b), 1.0):
                        diffs.append(f"{k}[{i}]: {a} != {b} (diff {abs(a-b)})")
    else:
        if exp_v is None or act_v is None:
            if exp_v != act_v:
                diffs.append(f"{k}: {act_v} != {exp_v}")
        elif isinstance(act_v, str):
            if act_v != exp_v:
                diffs.append(f"{k}: {act_v} != {exp_v}")
        else:
            if abs(act_v - exp_v) > 1e-7 * max(abs(exp_v), 1.0):
                diffs.append(f"{k}: {act_v} != {exp_v} (diff {abs(act_v - exp_v)})")

if not diffs:
    print("ALL 55 FIELDS MATCH THE WORKBOOK PERFECTLY!")
else:
    print(f"Found {len(diffs)} differences:")
    for d in diffs[:10]:
        print(" ", d)
