import json, openpyxl

with open('inputs/base_case.json') as f:
    base_case = json.load(f)
print("Base case keys:", list(base_case.keys()))

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=False)
print("Sheet names:", wb.sheetnames)

for sheet in wb.sheetnames:
    ws = wb[sheet]
    print(f"\n--- {sheet} ---")
    for r in range(1, min(ws.max_row+1, 25)):
        row_vals = [ws.cell(r, c).value for c in range(1, min(ws.max_column+1, 15))]
        if any(v is not None for v in row_vals):
            print(f"Row {r}: {row_vals[:10]}")
