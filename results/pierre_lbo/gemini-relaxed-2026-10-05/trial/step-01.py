import json
import openpyxl

with open('inputs/base_case.json') as f:
    base_case = json.load(f)
print("Base case keys:", list(base_case.keys()))
print("Sample base case:", json.dumps(base_case, indent=2)[:500])

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=False)
print("Sheet names:", wb.sheetnames)
