"""
train_delay_duration_model.py
==============================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Delay-duration regression model.

The Week-1 XGBoost classifier answers "will this shipment be delayed?"
(P(Delay | X)). The Week-2 optimization engine additionally needs "by how
many days?" as an input to size mitigation actions (e.g. is Air Freight's
2-day residual delay actually an improvement over the status quo?).

This script trains a lightweight XGBoost regressor, reusing the exact same
fitted Week-1 preprocessing pipeline and feature set, with target:

    Delay_Days = max(Lead_Time - Expected_Lead_Time, 0)

The model is intentionally NOT a replacement for or improvement of the
Week-1 classifier — it is a new, separate estimation target required as an
optimization input, per the Week-2 scope.

Usage
-----
    python scripts/train_delay_duration_model.py

Output
------
    engine/delay_duration_model.joblib

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from preprocessing import RANDOM_SEED  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("train_delay_duration_model")

DATASET_PATH = os.path.join("dataset", "supply_chain_mock.csv")
ENGINE_DIR = "engine"
PREPROCESSING_PIPELINE_PATH = os.path.join(ENGINE_DIR, "preprocessing_pipeline.pkl")
DURATION_MODEL_PATH = os.path.join(ENGINE_DIR, "delay_duration_model.joblib")


class DurationModelTrainingError(Exception):
    """Raised when a fatal error occurs during duration-model training."""


def main() -> None:
    """Train and serialize the delay-duration regressor."""
    try:
        if not os.path.exists(DATASET_PATH):
            raise DurationModelTrainingError(f"Dataset not found at '{DATASET_PATH}'.")
        if not os.path.exists(PREPROCESSING_PIPELINE_PATH):
            raise DurationModelTrainingError(
                f"Fitted preprocessing pipeline not found at '{PREPROCESSING_PIPELINE_PATH}'. "
                "Run Week-1 scripts/train_model.py first."
            )

        df = pd.read_csv(DATASET_PATH, parse_dates=["Order_Date"])
        df = df.drop_duplicates().reset_index(drop=True)
        logger.info("Loaded %d rows for delay-duration model training.", len(df))

        pipeline = joblib.load(PREPROCESSING_PIPELINE_PATH)

        y = np.clip(df["Lead_Time"] - df["Expected_Lead_Time"], 0, None).values
        X_full = pipeline.transform(df.copy())
        X = X_full[pipeline.artifacts.feature_columns]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_SEED
        )

        model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=350,
            max_depth=5,
            learning_rate=0.06,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=3,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        y_pred = np.clip(model.predict(X_test), 0, None)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        logger.info("Delay-duration model performance -> MAE: %.2f days | R^2: %.3f", mae, r2)

        os.makedirs(ENGINE_DIR, exist_ok=True)
        joblib.dump(model, DURATION_MODEL_PATH)
        logger.info("Saved delay-duration regressor to '%s'.", DURATION_MODEL_PATH)

    except DurationModelTrainingError as exc:
        logger.error("Duration model training failed: %s", exc)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during duration model training: %s", exc)
        raise


if __name__ == "__main__":
    main()
