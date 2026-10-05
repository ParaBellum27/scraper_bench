import json
import datetime
import math
import openpyxl

# Load base case input
with open('inputs/base_case.json') as f:
    inputs = json.load(f)

# Load workbook values
wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=True)
ws_forecast = wb['Forecast']
ws_debt = wb['Debt']
ws_returns = wb['Returns']

print("Loaded input and workbook.")
