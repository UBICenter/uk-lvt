from openfisca_uk.api import *
import pandas as pd
from tqdm import tqdm
from ubicenter import format_fig
import plotly.express as px

IMPUTED_LAND_VALUE = pd.read_csv("frs_hh_pred_land.csv").pred_land

def lvt_ubi_reform(rate: float, add_UBI: bool = True, baseline: Microsimulation = None) -> Reform:
    class land_value(Variable):
        entity = Household
        definition_period = YEAR
        value_type = float

    class LVT(Variable):
        entity = Household
        definition_period = YEAR
        value_type = float

        def formula(household, period, parameters):
            return rate * household("land_value", period)
    
    class tax(BASELINE_VARIABLES.tax):
        def formula(person, period, parameters):
            LVT_charge = person.household("LVT", period) * person("is_household_head", period)
            original_tax = BASELINE_VARIABLES.tax.formula(person, period, parameters)
            return original_tax + LVT_charge

    tax_reform = (
        reforms.structural.new_variable(land_value),
        reforms.structural.new_variable(LVT),
        reforms.structural.restructure(tax)
    )
    
    baseline = baseline or Microsimulation()
    tax_reform_sim = Microsimulation(tax_reform)
    tax_reform_sim.simulation.set_input("land_value", 2021, IMPUTED_LAND_VALUE)
    revenue = baseline.calc("net_income").sum() - tax_reform_sim.calc("net_income").sum()
    UBI_amount = revenue / baseline.calc("people").sum()

    if not add_UBI:
        UBI_amount = 0

    class UBI(Variable):
        entity = Person
        definition_period = YEAR
        value_type = float

        def formula(person, period, parameters):
            return UBI_amount
    
    class benefits(BASELINE_VARIABLES.benefits):
        def formula(person, period, parameters):
            original_benefits = BASELINE_VARIABLES.benefits.formula(person, period, parameters)
            return original_benefits + person("UBI", period)
    
    UBI_reform = (
        reforms.structural.new_variable(UBI),
        reforms.structural.restructure(benefits)
    )

    return tax_reform, UBI_reform

lvt_only = lvt_ubi_reform(rate=0.01, add_UBI=False)
lvt_1, lvt_2, lvt_3, lvt_4, lvt_5 = [lvt_ubi_reform(rate) for rate in (0.01, 0.02, 0.03, 0.04, 0.05)]

lvt_reforms = lvt_only, lvt_1, lvt_2, lvt_3, lvt_4, lvt_5
lvt_names = "LVT only", "1% LVT", "2% LVT", "3% LVT", "4% LVT", "5% LVT"

def pct_change(x, y):
    return (y - x) / x


def get_stats(reform_objects, reform_names):
    baseline = Microsimulation()
    income = baseline.calc("household_net_income", map_to="person")
    reform_sims = [Microsimulation(reform_object) for reform_object in reform_objects]
    effects = {
        "Poverty": [],
        "Deep poverty": [],
        "Adult poverty": [],
        "Child poverty": [],
        "Senior poverty": [],
        "Inequality": [],
        "Winner share": [],
        "Loser share": [],
        "UBI": [],
    }
    is_adult = baseline.calc("is_WA_adult")
    is_child = baseline.calc("is_child")
    is_senior = baseline.calc("is_SP_age")
    for sim in tqdm(reform_sims, desc="Simulating reforms"):
        sim.simulation.set_input("land_value", 2021, IMPUTED_LAND_VALUE)
        change = sim.calc("household_net_income", map_to="person") - income
        effects["Poverty"] += [pct_change(
            baseline.calc("in_poverty_bhc", map_to="person").mean(),
            sim.calc("in_poverty_bhc", map_to="person").mean())
        ]
        effects["Deep poverty"] += [pct_change(
            baseline.calc("in_deep_poverty_bhc", map_to="person").mean(),
            sim.calc("in_deep_poverty_bhc", map_to="person").mean())
        ]
        effects["Adult poverty"] += [pct_change(
            baseline.calc("in_poverty_bhc", map_to="person")[is_adult].mean(),
            sim.calc("in_poverty_bhc", map_to="person")[is_adult].mean())
        ]
        effects["Child poverty"] += [pct_change(
            baseline.calc("in_poverty_bhc", map_to="person")[is_child].mean(),
            sim.calc("in_poverty_bhc", map_to="person")[is_child].mean())
        ]
        effects["Senior poverty"] += [pct_change(
            baseline.calc("in_poverty_bhc", map_to="person")[is_senior].mean(),
            sim.calc("in_poverty_bhc", map_to="person")[is_senior].mean())
        ]
        effects["Inequality"] += [pct_change(
            baseline.calc("household_net_income", map_to="person").gini(),
            sim.calc("household_net_income", map_to="person").gini())
        ]
        effects["Winner share"] += [(change > 0).mean()]
        effects["Loser share"] += [(change < 0).mean()]
        effects["UBI"] += [sim.calc("UBI").max()]
    results = pd.DataFrame(effects)
    results.index = reform_names
    return results

def get_decile_chart(reform, baseline=None, **kwargs):
    baseline = baseline or Microsimulation()
    reformed = Microsimulation(reform)
    reformed.set_input("land_value", 2021, IMPUTED_LAND_VALUE)
    income = baseline.calc("household_net_income", map_to="person")
    change = reformed.calc("household_net_income", map_to="person") - income

    decile_changes = change.groupby(income.decile_rank()).sum() / income.groupby(income.decile_rank()).sum()

    return format_fig(px.bar(decile_changes).update_layout(title="Changes to net income", yaxis_tickformat="%", xaxis_title="Income decile", yaxis_title="Change to net income"))

df = get_stats(lvt_reforms, lvt_names)
df.to_csv("results.csv")