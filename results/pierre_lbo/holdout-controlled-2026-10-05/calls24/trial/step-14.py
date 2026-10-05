import json, calendar
from datetime import date, datetime
import openpyxl

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=True)
forecast = wb['Forecast']
debt = wb['Debt']
returns = wb['Returns']

with open('inputs/base_case.json') as f:
    inp = json.load(f)

# Import solve from previous code
from solution_test import solve # Wait, we haven't saved it to solution_test.py, let's execute in-line
