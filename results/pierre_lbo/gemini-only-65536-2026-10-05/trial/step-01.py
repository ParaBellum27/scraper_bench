import json, os, openpyxl

print("Files in workspace:", os.listdir("."))
if os.path.exists("inputs"):
    print("Files in inputs:", os.listdir("inputs"))

with open("inputs/base_case.json") as f:
    base_case = json.load(f)
print("Base case keys:", list(base_case.keys()))

wb = openpyxl.load_workbook("pierre_lbo_one.xlsx", data_only=False)
print("Sheet names:", wb.sheetnames)
