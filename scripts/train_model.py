"""
train_model.py
===============

SupplyPrescript - Week 1 Predictive Analytics Engine
Model training, hyperparameter tuning, and serialization.

Trains an XGBoost binary classifier to predict P(Delay | X) for a shipment,
using RandomizedSearchCV with Stratified K-Fold cross validation for
hyperparameter tuning. Serializes the fitted model and preprocessing
artifacts to the `engine/` directory for downstream use by the evaluation
and prediction scripts.

Usage
-----
    python scripts/train_model.py

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
import os
import sys
import time

import joblib
import numpy as np
import pandas as pd
from scipy.stats import randint, uniform
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from xgboost import XGBClassifier

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from preprocessing import PreprocessingPipeline, RANDOM_SEED, TARGET_COLUMN  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("train_model")

DATASET_PATH = os.path.join("dataset", "supply_chain_mock.csv")
ENGINE_DIR = "engine"
MODEL_PATH = os.path.join(ENGINE_DIR, "xgboost_model.joblib")
FEATURE_COLUMNS_PATH = os.path.join(ENGINE_DIR, "feature_columns.pkl")
LABEL_ENCODERS_PATH = os.path.join(ENGINE_DIR, "label_encoders.pkl")
PREPROCESSING_PIPELINE_PATH = os.path.join(ENGINE_DIR, "preprocessing_pipeline.pkl")
TRAIN_TEST_SPLIT_PATH = os.path.join(ENGINE_DIR, "train_test_split.pkl")


class ModelTrainingError(Exception):
    """Raised when a fatal error occurs during the training workflow."""


def load_dataset(path: str) -> pd.DataFrame:
    """Load the raw supply chain dataset from disk with error handling."""
    if not os.path.exists(path):
        raise ModelTrainingError(
            f"Dataset not found at '{path}'. Run scripts/generate_dataset.py first."
        )
    try:
        df = pd.read_csv(path, parse_dates=["Order_Date"])
    except Exception as exc:  # noqa: BLE001
        raise ModelTrainingError(f"Failed to load dataset from '{path}': {exc}") from exc

    logger.info("Loaded dataset with shape %s from '%s'.", df.shape, path)
    return df


def build_search_space() -> dict:
    """Define the hyperparameter search space for RandomizedSearchCV."""
    return {
        "learning_rate": uniform(0.01, 0.29),          # 0.01 - 0.30
        "max_depth": randint(3, 10),                    # 3 - 9
        "n_estimators": randint(150, 650),               # 150 - 649
        "subsample": uniform(0.6, 0.4),                  # 0.6 - 1.0
        "colsample_bytree": uniform(0.6, 0.4),           # 0.6 - 1.0
        "gamma": uniform(0.0, 5.0),                      # 0 - 5
        "min_child_weight": randint(1, 10),              # 1 - 9
    }


def tune_hyperparameters(X_train: pd.DataFrame, y_train: pd.Series) -> XGBClassifier:
    """
    Run RandomizedSearchCV with Stratified K-Fold cross validation to find
    strong XGBoost hyperparameters, then return the best fitted estimator.
    """
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    logger.info("Computed scale_pos_weight=%.3f to counter class imbalance.", scale_pos_weight)

    base_estimator = XGBClassifier(
        objective="binary:logistic",
        eval_metric="auc",
        tree_method="hist",
        random_state=RANDOM_SEED,
        scale_pos_weight=scale_pos_weight,
        n_jobs=-1,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

    n_iter = int(os.environ.get("SP_SEARCH_ITER", "30"))

    search = RandomizedSearchCV(
        estimator=base_estimator,
        param_distributions=build_search_space(),
        n_iter=n_iter,
        scoring="roc_auc",
        cv=cv,
        verbose=1,
        random_state=RANDOM_SEED,
        n_jobs=-1,
        refit=True,
    )

    logger.info("Starting RandomizedSearchCV: %d candidates x 5 folds = %d fits.", n_iter, n_iter * 5)
    start = time.time()
    search.fit(X_train, y_train)
    elapsed = time.time() - start
    logger.info("Hyperparameter search complete in %.1fs.", elapsed)
    logger.info("Best CV ROC AUC: %.4f", search.best_score_)
    logger.info("Best hyperparameters: %s", search.best_params_)

    return search.best_estimator_


def save_artifacts(model: XGBClassifier, pipeline: PreprocessingPipeline,
                    X_test: pd.DataFrame, y_test: pd.Series) -> None:
    """Serialize the model and all preprocessing artifacts with joblib."""
    os.makedirs(ENGINE_DIR, exist_ok=True)

    joblib.dump(model, MODEL_PATH)
    logger.info("Saved trained model to '%s'.", MODEL_PATH)

    joblib.dump(pipeline.artifacts.feature_columns, FEATURE_COLUMNS_PATH)
    logger.info("Saved feature columns to '%s'.", FEATURE_COLUMNS_PATH)

    joblib.dump(pipeline.artifacts.label_encoders or pipeline.artifacts.ordinal_mappings, LABEL_ENCODERS_PATH)
    logger.info("Saved label/ordinal encoders to '%s'.", LABEL_ENCODERS_PATH)

    joblib.dump(pipeline, PREPROCESSING_PIPELINE_PATH)
    logger.info("Saved full preprocessing pipeline to '%s'.", PREPROCESSING_PIPELINE_PATH)

    joblib.dump({"X_test": X_test, "y_test": y_test}, TRAIN_TEST_SPLIT_PATH)
    logger.info("Saved held-out test split to '%s' for downstream evaluation.", TRAIN_TEST_SPLIT_PATH)


def main() -> None:
    """Entry point: load data, preprocess, tune, train, and serialize."""
    try:
        df = load_dataset(DATASET_PATH)

        pipeline = PreprocessingPipeline()
        processed_df = pipeline.fit_transform(df)

        X_train, X_test, y_train, y_test = pipeline.split(processed_df, test_size=0.2)

        best_model = tune_hyperparameters(X_train, y_train)

        # Refit on the full training set with early-stopping-friendly
        # n_estimators already selected by the search (already refit=True
        # by RandomizedSearchCV, so best_model is trained on all of X_train).

        save_artifacts(best_model, pipeline, X_test, y_test)

        logger.info("Training pipeline finished successfully.")
    except ModelTrainingError as exc:
        logger.error("Training failed: %s", exc)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during training: %s", exc)
        raise


if __name__ == "__main__":
    main()
