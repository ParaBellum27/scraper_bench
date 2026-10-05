import os, json, openpyxl

print("Files in workspace:", os.listdir('.'))
with open('inputs/base_case.json') as f:
    base_case = json.load(f)
print("Base case keys:", list(base_case.keys()))

wb = openpyxl.load_workbook('pierre_lbo_one.xlsx', data_only=False)
print("Sheet names:", wb.sheetnames)
