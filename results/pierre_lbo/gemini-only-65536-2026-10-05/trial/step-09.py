deal_mom = 319610.739315068 / 50415.9999999999
holding_period_years = 4.83287671232877

deal_irr_calc = deal_mom ** (1.0 / holding_period_years) - 1.0
print("deal_irr calculated:", repr(deal_irr_calc))
print("deal_irr in Excel:   ", repr(0.465405016757732))
print("diff:                ", abs(deal_irr_calc - 0.465405016757732))

sponsor_mom = 294231.451796554 / 49911.8399999999
sponsor_irr_calc = sponsor_mom ** (1.0 / holding_period_years) - 1.0
print("sponsor_irr calc:    ", repr(sponsor_irr_calc))
print("sponsor_irr in Excel:", repr(0.44353014476164))
print("diff:                ", abs(sponsor_irr_calc - 0.44353014476164))

mgmt_mom = 25379.287518514 / 504.159999999999
mgmt_irr_calc = mgmt_mom ** (1.0 / holding_period_years) - 1.0
print("mgmt_irr calc:       ", repr(mgmt_irr_calc))
print("mgmt_irr in Excel:   ", repr(1.24984601299547))
print("diff:                ", abs(mgmt_irr_calc - 1.24984601299547))
