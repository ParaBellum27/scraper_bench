import math

holding_period_years = (wb["Returns"]["B13"].value - wb["Returns"]["B7"].value).days / 365.0
deal_inv = 50415.9999999999
deal_proc = 319610.739315068
deal_irr_formula = (deal_proc / deal_inv) ** (1.0 / holding_period_years) - 1.0
excel_deal_irr = wb["Returns"]["B37"].value

print(f"Formula: {deal_irr_formula:.12f}")
print(f"Excel:   {excel_deal_irr:.12f}")
print(f"Diff:    {abs(deal_irr_formula - excel_deal_irr)}")

spon_inv = wb["Returns"]["B10"].value
spon_proc = wb["Returns"]["B30"].value
spon_irr_formula = (spon_proc / spon_inv) ** (1.0 / holding_period_years) - 1.0
excel_spon_irr = wb["Returns"]["B38"].value
print(f"Spon diff: {abs(spon_irr_formula - excel_spon_irr)}")

mgmt_inv = wb["Returns"]["B11"].value
mgmt_proc = wb["Returns"]["B31"].value
mgmt_irr_formula = (mgmt_proc / mgmt_inv) ** (1.0 / holding_period_years) - 1.0
excel_mgmt_irr = wb["Returns"]["B39"].value
print(f"Mgmt diff: {abs(mgmt_irr_formula - excel_mgmt_irr)}")
