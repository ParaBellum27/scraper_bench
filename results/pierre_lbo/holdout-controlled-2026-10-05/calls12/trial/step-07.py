import math

# From Returns sheet:
deal_equity = 50415.9999999999
deal_proceeds = 319610.739315068
holding_years = 4.83287671232877

sheet_deal_irr = 0.465405016757732
calc_irr = (deal_proceeds / deal_equity) ** (1.0 / holding_years) - 1.0
print("Sheet deal IRR:", sheet_deal_irr)
print("Calc deal IRR: ", calc_irr)
print("Diff:          ", abs(calc_irr - sheet_deal_irr))

# Sponsor
sponsor_inv = 49911.8399999999
sponsor_proc = 294231.451796554
sheet_sponsor_irr = 0.44353014476164
calc_sponsor_irr = (sponsor_proc / sponsor_inv) ** (1.0 / holding_years) - 1.0
print("\nSheet sponsor IRR:", sheet_sponsor_irr)
print("Calc sponsor IRR: ", calc_sponsor_irr)
print("Diff:            ", abs(calc_sponsor_irr - sheet_sponsor_irr))

# Management
mgmt_inv = 504.159999999999
mgmt_proc = 25379.287518514
sheet_mgmt_irr = 1.24984601299547
calc_mgmt_irr = (mgmt_proc / mgmt_inv) ** (1.0 / holding_years) - 1.0
print("\nSheet mgmt IRR:", sheet_mgmt_irr)
print("Calc mgmt IRR: ", calc_mgmt_irr)
print("Diff:         ", abs(calc_mgmt_irr - sheet_mgmt_irr))
