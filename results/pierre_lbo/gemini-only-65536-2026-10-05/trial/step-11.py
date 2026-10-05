import json, datetime, calendar, openpyxl

wb = openpyxl.load_workbook("pierre_lbo_one.xlsx", data_only=True)
ws_ret = wb["Returns"]
ws_fc = wb["Forecast"]
ws_debt = wb["Debt"]

# Load our calculated dict
# Let's run a test comparison
def compare(name, actual, expected, tol=1e-7):
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        print(f"MISMATCH in {name}: actual={actual}, expected={expected}")
        return False
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        diff = abs(actual - expected)
        rel_diff = diff / max(abs(expected), 1.0)
        if diff > tol and rel_diff > tol:
            print(f"MISMATCH in {name}: actual={actual}, expected={expected}, diff={diff}")
            return False
        return True
    if actual != expected:
        print(f"MISMATCH in {name}: actual={actual}, expected={expected}")
        return False
    return True

# Compare fields:
# We have 2 calls remaining. Let's do a complete check and prepare solution.py.
# Then call submit=True on the last call.
