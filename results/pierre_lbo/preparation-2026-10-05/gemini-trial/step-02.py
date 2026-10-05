import openpyxl

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=False)

def print_sheet(ws, max_r=15, max_c=30):
    for r in range(1, max_r + 1):
        row_vals = [ws.cell(r, c).value for c in range(1, max_c + 1)]
        if any(v is not None for v in row_vals):
            # print non-empty or header
            formatted = [f"Col{c}: {row_vals[c-1]}" for c in range(1, len(row_vals)+1) if row_vals[c-1] is not None]
            print(f"Row {r:2d}: " + " | ".join(formatted))

print("=== FORECAST SHEET ===")
print_sheet(wb['Forecast'], max_r=13, max_c=25)

print("\n=== DEBT SHEET ===")
print_sheet(wb['Debt'], max_r=13, max_c=30)

print("\n=== RETURNS SHEET ===")
print_sheet(wb['Returns'], max_r=50, max_c=10)
