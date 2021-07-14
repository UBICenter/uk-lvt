import numpy as np
import pandas as pd
import microdf as mdf
import synthimpute as si
import sklearn
from openfisca_uk import Microsimulation

sim = Microsimulation(year=2020)

was = pd.read_csv("~/was.csv")

TRAIN_COLS = [
    "gross_income",
    "num_adults",
    "num_children",
    "pension_income",
    "employment_income",
    "self_employment_income",
    "investment_income",
    "num_bedrooms",
    "council_tax",
    # "tenure_type", # TODO: map this to is_renter in WAS.
    # "region"  # TODO: add region mapping from WAS int.
]

IMPUTE_COLS = [
    "est_land",  # Total wealth.
]

# TODO: Test imputation quantiles on a hold out sample.
train, test = sklearn.model_selection.train_test_split(was)
test["pred_land"] = si.rf_impute(
    x_train=train[TRAIN_COLS],
    y_train=train[IMPUTE_COLS],
    x_new=test[TRAIN_COLS],
    sample_weight_train=train.weight,
)

# FRS has investment income split between dividend and savings interest.
frs_cols = [i for i in TRAIN_COLS if i != "investment_income"]
frs_cols += [
    "dividend_income",
    "savings_interest_income",
    "people",
    "net_income",
]
frs_cols

frs = sim.df(frs_cols, map_to="household")
frs["investment_income"] = frs.savings_interest_income + frs.dividend_income

frs["pred_land"] = si.rf_impute(
    x_train=was[TRAIN_COLS],
    y_train=was[IMPUTE_COLS],
    x_new=frs[TRAIN_COLS],
    sample_weight_train=was.weight,
)

# Adjust the imputed land values to match the actual land values.
total_initial_pred_land = frs.pred_land.sum()

total_was_land = mdf.weighted_sum(was, "est_land", "weight")

frs.pred_land *= total_was_land / total_initial_pred_land

frs.pred_land.to_csv("frs_hh_pred_land.csv", index=False)
