import json, openpyxl

with open("inputs/base_case.json") as f:
    base_case = json.load(f)

print("base_case JSON summary:")
for k, v in base_case.items():
    if isinstance(v, (dict, list)):
        print(f"  {k}: {type(v)} len/keys {len(v)}")
    else:
        print(f"  {k}: {v}")

wb_data = openpyxl.load_workbook("pierre_lbo_one.xlsx", data_only=True)
wb_formula = openpyxl.load_workbook("pierre_lbo_one.xlsx", data_only=False)

for name in wb_data.sheetnames:
    print(f"\n--- Sheet: {name} ---")
    ws_d = wb_data[name]
    ws_f = wb_formula[name]
    for r in range(1, min(ws_d.max_row + 1, 45)):
        row_vals = [ws_d.cell(r, c).value for c in range(1, min(ws_d.max_column + 1, 15))]
        row_forms = [ws_f.cell(r, c).value for c in range(1, min(ws_f.max_column + 1, 15))]
        # print non-empty rows
        if any(v is not None for v in row_vals):
            print(f"Row {r:2d}: vals={row_vals[:10]}")
            # print formulas if different from values
            formulas_only = [f if str(f).startswith('=') else '' for f in row_forms[:10]]
            if any(formulas_only):
                print(f"       forms={formulas_only}")
