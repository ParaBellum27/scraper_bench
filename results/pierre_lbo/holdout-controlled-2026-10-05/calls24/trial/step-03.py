import openpyxl

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=False)
wb_val = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=True)

def dump_sheet(sheet_name, max_r=20, max_c=30):
    ws = wb[sheet_name]
    ws_val = wb_val[sheet_name]
    print(f"\n================ SHEET: {sheet_name} ================")
    # Print headers (row 4 usually)
    for r in range(1, max_r+1):
        row_str = []
        for c in range(1, max_c+1):
            cell = ws.cell(r, c)
            val_cell = ws_val.cell(r, c)
            col_letter = openpyxl.utils.get_column_letter(c)
            if cell.value is not None or val_cell.value is not None:
                if str(cell.value).startswith('='):
                    row_str.append(f"{col_letter}{r}: {cell.value} [{val_cell.value}]")
                else:
                    row_str.append(f"{col_letter}{r}: {val_cell.value}")
        if row_str:
            print(f"Row {r}: " + " | ".join(row_str))

dump_sheet('Forecast', 14, 25)
dump_sheet('Debt', 14, 30)
dump_sheet('Returns', 50, 6)
