import openpyxl

wb_d = openpyxl.load_workbook("pierre_lbo_one.xlsx", data_only=True)
ws_forecast = wb_d["Forecast"]
ws_debt = wb_d["Debt"]

print("Forecast rows 5 to 13:")
for r in range(5, 13):
    print(f"Row {r} (Period {ws_forecast.cell(r, 1).value}): dates={ws_forecast.cell(r, 3).value}, rev={ws_forecast.cell(r, 12).value}")

print("\nDebt rows 5 to 13:")
for r in range(5, 13):
    print(f"Row {r} (Period {ws_debt.cell(r, 1).value}): eval={ws_debt.cell(r, 2).value}, cash_bal={ws_debt.cell(r, 28).value}")
