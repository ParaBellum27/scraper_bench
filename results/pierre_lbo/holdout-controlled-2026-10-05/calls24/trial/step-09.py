wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=False)
ws = wb['Debt']

for col in range(1, 29):
    header = ws.cell(4, col).value
    f5 = ws.cell(5, col).value
    f6 = ws.cell(6, col).value
    col_let = openpyxl.utils.get_column_letter(col)
    print(f"Col {col_let} ({header}):")
    print(f"   Row 5: {f5}")
    print(f"   Row 6: {f6}")
