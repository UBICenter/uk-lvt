import pandas as pd
import microdf as mdf

RENAMES = {
    "R6xshhwgt": "weight",
    # Components for estimating land holdings.
    "DVLUKValR6_sum": "uk_land",
    "DVPropertyR6": "property_values",
    "DVFESHARESR6_aggr": "emp_shares_options",
    "DVFShUKVR6_aggr": "uk_shares",
    "DVIISAVR6_aggr": "investment_isas",
    "DVFCollVR6_aggr": "unit_investment_trusts",
    "TotpenR6_aggr": "pensions",
    "DvvalDBTR6_aggr": "db_pensions",
    # Predictors for fusing to FRS.
    "dvtotgirR6": "gross_income",
    "NumAdultW6": "num_adults",
    "NumCh18W6": "num_children",
    # Household Gross Annual income from occupational or private pensions
    "DVGIPPENR6_AGGR": "pension_income",
    "DVGISER6_AGGR": "self_employment_income",
    # Household Gross annual income from investments
    "DVGIINVR6_aggr": "investment_income",
    # Household Total Annual Gross employee income
    "DVGIEMPR6_AGGR": "employment_income",
    # Other columns for reference.
    "DVLOSValR6_sum": "non_uk_land",
    "HFINWNTR6_Sum": "net_financial_wealth",
    "DVLUKDebtR6_sum": "uk_land_debt",
    "HFINWR6_Sum": "gross_financial_wealth",
    "TotWlthR6": "wealth",
}

was = (
    pd.read_csv(
        "~/was_round_6_hhold_eul_mar_20.tab",
        usecols=RENAMES.keys(),
        delimiter="\t",
    )
    .replace(" ", 0)
    .astype(float)
    .rename(columns=RENAMES)
)

# Land value held by households and non-profit institutions serving
# households: 3.9tn as of 2019 (ONS).
HH_NP_LAND_VALUE = 3_912_632e6
# Land value held by financial and non-financial corporations.
CORP_LAND_VALUE = 1_600_038e6
# Land value held by government (not used).
GOV_LAND_VALUE = 196_730e6

was["non_db_pensions"] = was.pensions - was.db_pensions
was["corp_wealth"] = was[
    [
        "non_db_pensions",
        "emp_shares_options",
        "uk_shares",
        "investment_isas",
        "unit_investment_trusts",
    ]
].sum(axis=1)

totals = mdf.weighted_sum(
    was, ["uk_land", "property_values", "corp_wealth"], "weight"
)

land_prop_share = (HH_NP_LAND_VALUE - totals.uk_land) / totals.property_values
land_corp_share = CORP_LAND_VALUE / totals.corp_wealth

was["est_land"] = (
    was.uk_land
    + was.property_values * land_prop_share
    + was.corp_wealth * land_corp_share
)

print(mdf.weighted_sum(was, "est_land", "weight"))

was.to_csv("~/was.csv", index=False)
