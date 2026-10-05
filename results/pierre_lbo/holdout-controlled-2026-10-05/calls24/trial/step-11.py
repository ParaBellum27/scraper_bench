import math

# From Returns sheet:
entry_equity = 50415.9999999999
sponsor_investment = 49911.8399999999
management_investment = 504.159999999999

equity_proceeds = 319610.739315068
sponsor_proceeds = 294231.451796554
management_proceeds = 25379.287518514

holding_period_years = 4.83287671232877

# Workbook values:
deal_irr_wb = 0.465405016757732
sponsor_irr_wb = 0.44353014476164
management_irr_wb = 1.24984601299547

# Analytical values:
deal_irr = (equity_proceeds / entry_equity) ** (1.0 / holding_period_years) - 1
sponsor_irr = (sponsor_proceeds / sponsor_investment) ** (1.0 / holding_period_years) - 1
management_irr = (management_proceeds / management_investment) ** (1.0 / holding_period_years) - 1

print(f"Deal IRR:       {deal_irr:.15f} vs {deal_irr_wb:.15f}, diff={abs(deal_irr - deal_irr_wb)}")
print(f"Sponsor IRR:    {sponsor_irr:.15f} vs {sponsor_irr_wb:.15f}, diff={abs(sponsor_irr - sponsor_irr_wb)}")
print(f"Management IRR: {management_irr:.15f} vs {management_irr_wb:.15f}, diff={abs(management_irr - management_irr_wb)}")
