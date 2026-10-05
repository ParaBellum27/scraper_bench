"""Private deterministic stress inputs; no oracle or workbook dependencies."""

from copy import deepcopy
import random


def _controlled(base):
    """A transparent 365-day hold inside a 366-day fiscal year."""
    value = deepcopy(base)
    value.update(case=1, last_fiscal_year_end="2023-12-01", deal_date="2023-12-02",
                 exit_period=1, opening_revenue=1464.0, opening_working_capital=0.0,
                 entry_multiple=1.0, exit_multiple=1.0, exit_fee_rate=0.0,
                 tax_rate=0.0, ordinary_equity_fraction=0.5,
                 management_ordinary_fraction=0.2, preferred_pik_rate=0.0,
                 working_capital_ratio=[0.0] * 8)
    value["term_loan"] = dict(principal=100.0, cash_rate=0.0, pik_rate=0.0,
                              amortization_rate=0.0, cash_sweep=0.0, maturity_period=20)
    value["revolver"] = dict(commitment=1000.0, cash_rate=0.1, maturity_period=20)
    profile = dict(revenue_growth=[0.0] * 8, gross_profit_margin=[0.5] * 8,
                   opex_margin=[0.25] * 8, capex=[366.0] * 8)
    value["scenarios"] = [deepcopy(profile) for _ in range(4)]
    return value


def generate_hidden_cases(base, seed=20261004):
    """Return fresh {name, inputs} rows without modifying base or global RNG state."""
    cases = []

    def add(name, value=None):
        value = deepcopy(base if value is None else value)
        cases.append({"name": name, "inputs": value})
        return value

    for profile in range(1, 5):
        if profile != base["case"]:
            add(f"original_profile_{profile}")["case"] = profile
    for name, key, value in (
        ("entry_multiple_shock", "entry_multiple", 10.5),
        ("exit_multiple_shock", "exit_multiple", 5.0),
        ("exit_fee_shock", "exit_fee_rate", 0.12),
        ("tax_shock", "tax_rate", 0.4),
        ("preferred_accretion_shock", "preferred_pik_rate", 0.2),
        ("ordinary_split_shock", "ordinary_equity_fraction", 0.7),
        ("management_share_shock", "management_ordinary_fraction", 0.4),
        ("early_exit", "exit_period", 1),
        ("full_horizon", "exit_period", 8),
    ):
        add(name)[key] = value
    for name, key, value in (
        ("cash_interest_shock", "cash_rate", 0.14),
        ("pik_interest_shock", "pik_rate", 0.09),
        ("scheduled_amortization", "amortization_rate", 0.18),
        ("cash_sweep", "cash_sweep", 0.75),
        ("term_maturity", "maturity_period", 2),
        ("entry_leverage_shock", "principal", base["term_loan"]["principal"] * 0.5),
    ):
        add(name)["term_loan"][key] = value
    interacting = add("interacting_finance_shocks")
    interacting.update(tax_rate=0.35, exit_multiple=6.5, preferred_pik_rate=0.13,
                       ordinary_equity_fraction=0.35, management_ordinary_fraction=0.25)
    interacting["term_loan"].update(cash_rate=0.1, pik_rate=0.04,
                                     amortization_rate=0.08, cash_sweep=0.5)
    controlled = _controlled(base)
    draw = add("revolver_draw_then_priority_repayment", controlled)
    draw["exit_period"] = 2
    draw["scenarios"][0]["capex"][0:2] = [466.0, 0.0]
    draw["term_loan"]["cash_sweep"] = 1.0
    draw["revolver"]["cash_rate"] = 0.17
    insufficient = add("first_period_liquidity_shortfall", draw)
    insufficient["revolver"]["commitment"] = 10.0
    later = add("later_period_liquidity_shortfall", controlled)
    later["exit_period"] = 3
    later["scenarios"][0]["capex"][1] = 2000.0
    later["revolver"]["commitment"] = 10.0
    refinancing = add("term_maturity_refinanced_by_revolver", controlled)
    refinancing["term_loan"]["maturity_period"] = 1
    refinancing["term_loan"]["pik_rate"] = 0.1
    maturity = add("revolver_maturity_no_redraw", controlled)
    maturity["exit_period"] = 2
    maturity["scenarios"][0]["capex"][0] = 466.0
    maturity["revolver"]["maturity_period"] = 2
    repaid = add("revolver_maturity_funded", maturity)
    repaid["scenarios"][0]["capex"][1] = 0.0
    capped = add("capped_sweep_and_amortization", controlled)
    capped["exit_period"] = 3
    capped["scenarios"][0]["capex"] = [0.0] * 8
    capped["term_loan"].update(amortization_rate=0.8, cash_sweep=1.0, pik_rate=0.02)
    for label, multiple in (("below", 232.0 / 366), ("at", 233.0 / 366), ("above", 234.0 / 366)):
        add(f"preferred_waterfall_{label}_boundary", controlled)["exit_multiple"] = multiple
    add("no_management_investment", controlled)["management_ordinary_fraction"] = 0.0
    add("no_ordinary_equity", controlled)["ordinary_equity_fraction"] = 0.0
    add("no_preferred_equity", controlled)["ordinary_equity_fraction"] = 1.0
    all_management = add("zero_sponsor_investment", controlled)
    all_management.update(ordinary_equity_fraction=1.0, management_ordinary_fraction=1.0)
    add("underwater_exit", controlled)["exit_multiple"] = 0.0
    losses = add("negative_exit_ebitda_no_negative_fees", controlled)
    losses["exit_period"] = 2
    losses["scenarios"][0]["opex_margin"][1] = 0.75
    losses["exit_fee_rate"] = 0.1
    losses["revolver"]["commitment"] = 2000.0
    wc = add("full_working_capital_in_short_stub", controlled)
    wc["deal_date"] = "2024-11-30"
    wc["working_capital_ratio"] = [0.1] * 8
    add("one_day_december_stub")["deal_date"] = "2022-11-30"
    leap = add("leap_day_sequential_clamp", controlled)
    leap.update(last_fiscal_year_end="2020-02-29", deal_date="2020-03-01", exit_period=5)
    leap["scenarios"][0]["capex"] = [0.0] * 8
    add("leap_day_close", controlled)["deal_date"] = "2024-02-29"
    for name, factor in (("currency_scale_small", 0.001), ("currency_scale_large", 1000.0)):
        scaled = add(name)
        scaled["opening_revenue"] *= factor
        scaled["opening_working_capital"] *= factor
        scaled["term_loan"]["principal"] *= factor
        scaled["revolver"]["commitment"] *= factor
        for profile in scaled["scenarios"]:
            profile["capex"] = [item * factor for item in profile["capex"]]
    rng = random.Random(seed)
    for index in range(4):
        mixed = add(f"seeded_operating_finance_mix_{index + 1}")
        mixed["case"] = index + 1
        mixed["exit_period"] = rng.randint(2, 6)
        mixed["exit_multiple"] = rng.uniform(4.5, 11.0)
        mixed["tax_rate"] = rng.uniform(0.15, 0.4)
        mixed["term_loan"]["cash_rate"] = rng.uniform(0.025, 0.12)
        mixed["term_loan"]["pik_rate"] = rng.uniform(0.0, 0.06)
        mixed["term_loan"]["cash_sweep"] = rng.uniform(0.0, 1.0)
        profile = mixed["scenarios"][index]
        profile["capex"] = [item * rng.uniform(0.7, 1.5) for item in profile["capex"]]
        mixed["working_capital_ratio"] = [item * rng.uniform(0.7, 1.4) for item in mixed["working_capital_ratio"]]
    return cases


def exercised_features(inputs, outputs):
    """Describe executed finance with witnesses, not assumptions from case names.

    Financing-flow period lists refer only to funded rows; operating forecasts
    and timing fractions retain the planned horizon. Failed obligations are
    labelled separately: a maturity shortfall is not a successful repayment.
    """
    features = {
        "operating_forecast": {"periods": len(outputs["revenue"])},
        "entry_funding": {"equity": outputs["entry_equity"]},
        "fiscal_dates": {"dates": outputs["dates"]},
    }
    for name, field in (
        ("stub_operations", "operating_fractions"),
        ("actual_365_interest_fractions", "interest_year_fractions"),
    ):
        periods = [i + 1 for i, value in enumerate(outputs[field]) if value != 1]
        if periods:
            features[name] = {"periods": periods, "fractions": outputs[field]}
    for field in (
        "change_working_capital", "cash_interest", "rcf_interest", "cash_taxes",
        "tlb_pik", "rcf_draw", "mandatory_rcf_repayment", "tlb_sweep",
    ):
        periods = [i + 1 for i, value in enumerate(outputs[field]) if value != 0]
        if periods:
            features[field] = {"periods": periods, "amounts": outputs[field]}
    maturity = inputs["term_loan"]["maturity_period"]
    for name, matured in (("scheduled_tlb_amortization", False), ("tlb_maturity_repayment", True)):
        periods = [
            i + 1 for i, value in enumerate(outputs["mandatory_tlb_repayment"])
            if value > 0 and ((i + 1 >= maturity) == matured)
        ]
        if periods:
            features[name] = {"periods": periods}
    voluntary = [
        total - mandatory for total, mandatory in
        zip(outputs["rcf_repayment"], outputs["mandatory_rcf_repayment"])
    ]
    if any(value > 0 for value in voluntary):
        features["voluntary_rcf_repayment"] = {
            "periods": [i + 1 for i, value in enumerate(voluntary) if value > 0],
            "amounts": voluntary,
        }
    if outputs["status"] == "liquidity_shortfall":
        period = outputs["failure_period"]
        features["liquidity_failure"] = {
            "period": period, "funding_shortfall": outputs["funding_shortfall"],
            "funded_periods": len(outputs["cash_balance"]),
        }
        if period >= maturity:
            features["failure_at_or_after_tlb_maturity"] = {"period": period}
        if period >= inputs["revolver"]["maturity_period"]:
            features["failure_with_revolver_redraw_prohibited"] = {"period": period}
        return features
    features["exit_equity_bridge"] = {
        "before_floor": outputs["equity_value_before_floor"],
        "proceeds": outputs["equity_proceeds"],
    }
    for field in ("exit_fees", "preferred_payout", "ordinary_payout"):
        if outputs[field] > 0:
            features[field] = {"amount": outputs[field]}
    if outputs["equity_value_before_floor"] < 0:
        features["equity_floor"] = {"before_floor": outputs["equity_value_before_floor"]}
    if outputs["exit_ev"] < 0:
        features["negative_ev_zero_fees"] = {"ev": outputs["exit_ev"], "fees": outputs["exit_fees"]}
    equity, preferred = outputs["equity_proceeds"], outputs["preferred_accrued"]
    if preferred > 0 and abs(equity - preferred) <= 1e-12 * equity:
        features["preferred_hurdle"] = {"equity": equity, "preferred_accrued": preferred}
    elif preferred > equity:
        features["preferred_not_fully_paid"] = {"equity": equity, "preferred_accrued": preferred}
    for owner in ("deal", "sponsor", "management"):
        investment = outputs["entry_equity"] if owner == "deal" else outputs[owner + "_investment"]
        if investment == 0:
            features[owner + "_zero_investment"] = {"mom": outputs[owner + "_mom"], "irr": outputs[owner + "_irr"]}
        elif outputs[owner + "_irr"] is None:
            features[owner + "_nonpositive_payout"] = {"irr": None}
        else:
            features[owner + "_dated_return"] = {
                "holding_years": outputs["holding_period_years"], "irr": outputs[owner + "_irr"],
            }
    return features
