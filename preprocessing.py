"""
preprocessing.py
=================

SupplyPrescript - Week 1 Predictive Analytics Engine
Data preprocessing and feature engineering pipeline.

This module implements a reusable, production-grade preprocessing pipeline:

    1. Missing value handling
    2. Duplicate removal
    3. Outlier detection / clipping (IQR method)
    4. Feature engineering (ratio and interaction features)
    5. Label encoding for ordinal/binary categoricals
    6. One-hot encoding for nominal categoricals
    7. Feature scaling (StandardScaler) for numeric features
    8. Feature selection (variance + correlation pruning)
    9. Train/test split (stratified, random_state=42)

All fitted transformers are wrapped in a single ``PreprocessingPipeline``
object that can be serialized with joblib and reused at inference time to
guarantee train/serve consistency.

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger("preprocessing")

RANDOM_SEED = 42

# Columns that must never be used as model features (identifiers, raw dates,
# or the label itself).
ID_AND_LEAKAGE_COLUMNS = ["Shipment_ID", "Supplier_ID", "Order_Date"]
TARGET_COLUMN = "Delay"

# Ordinal categorical -> explicit ordering used for label encoding so that
# the numeric encoding preserves real-world ordinal meaning.
ORDINAL_MAPPINGS = {
    "Supplier_Risk": {"Low": 0, "Medium": 1, "High": 2},
    "Order_Priority": {"Low": 0, "Medium": 1, "High": 2, "Critical": 3},
    "Production_Status": {"Delayed": 0, "On Schedule": 1, "Ahead of Schedule": 2},
}

# Nominal categorical columns -> one-hot encoded.
NOMINAL_COLUMNS = [
    "Supplier_Country", "Destination_Country", "Shipping_Mode", "Carrier",
    "Warehouse", "Customer_Type", "Packaging_Type", "Container_Type",
]

# Continuous numeric columns eligible for outlier clipping and scaling.
NUMERIC_COLUMNS = [
    "Supplier_Rating", "Lead_Time", "Expected_Lead_Time", "Historical_Delay_Count",
    "Inventory_Level", "Inventory_Days", "Demand_Forecast", "Weather_Severity",
    "Traffic_Index", "Fuel_Price", "Port_Congestion", "Distance",
    "Transportation_Cost", "Purchase_Order_Value", "Vehicle_Availability",
    "Quality_Score", "Inspection_Delay", "Customs_Clearance_Time",
    "Shipment_Weight", "Shipment_Volume", "Route_Risk", "Carbon_Emission",
    "Supplier_OnTime_Rate", "Late_Delivery_Cost", "Market_Demand_Index",
    "Geopolitical_Risk", "Economic_Index",
]

BINARY_COLUMNS = ["Holiday_Impact", "Temperature_Sensitive", "Fragile"]

CALENDAR_COLUMNS = ["Month", "Quarter", "Week", "Year"]


class DataValidationError(Exception):
    """Raised when the input dataset fails schema validation."""


@dataclass
class PreprocessingArtifacts:
    """Container for fitted preprocessing artifacts to be serialized."""

    label_encoders: dict = field(default_factory=dict)
    ordinal_mappings: dict = field(default_factory=lambda: ORDINAL_MAPPINGS)
    scaler: Optional[StandardScaler] = None
    feature_columns: Optional[list] = None
    numeric_columns: list = field(default_factory=lambda: list(NUMERIC_COLUMNS))
    nominal_columns: list = field(default_factory=lambda: list(NOMINAL_COLUMNS))
    ordinal_columns: list = field(default_factory=lambda: list(ORDINAL_MAPPINGS.keys()))
    binary_columns: list = field(default_factory=lambda: list(BINARY_COLUMNS))
    clip_bounds: dict = field(default_factory=dict)


class PreprocessingPipeline:
    """
    End-to-end preprocessing pipeline for the SupplyPrescript delay-prediction
    model.

    The pipeline separates ``fit_transform`` (used on training data) from
    ``transform`` (used on validation/test/inference data) to prevent data
    leakage, and stores every fitted parameter inside a
    :class:`PreprocessingArtifacts` instance that can be persisted with
    joblib for consistent inference-time behaviour.
    """

    def __init__(self):
        self.artifacts = PreprocessingArtifacts()
        self._is_fitted = False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @staticmethod
    def validate_schema(df: pd.DataFrame) -> None:
        """Validate that required columns are present in the input dataframe."""
        required = set(NUMERIC_COLUMNS + NOMINAL_COLUMNS + BINARY_COLUMNS + CALENDAR_COLUMNS
                       + list(ORDINAL_MAPPINGS.keys()))
        missing = required - set(df.columns)
        if missing:
            raise DataValidationError(f"Dataset is missing required columns: {sorted(missing)}")
        logger.info("Schema validation passed. %d columns verified.", len(required))

    # ------------------------------------------------------------------
    # Core steps
    # ------------------------------------------------------------------
    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """Remove exact duplicate rows, keeping the first occurrence."""
        before = len(df)
        df = df.drop_duplicates(keep="first").reset_index(drop=True)
        removed = before - len(df)
        logger.info("Removed %d duplicate rows.", removed)
        return df

    @staticmethod
    def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
        """
        Impute missing values.

        Numeric columns are imputed with the column median (robust to
        outliers); categorical columns are imputed with the column mode.
        """
        df = df.copy()
        for col in NUMERIC_COLUMNS:
            if col in df.columns and df[col].isna().any():
                median_val = df[col].median()
                n_missing = df[col].isna().sum()
                df[col] = df[col].fillna(median_val)
                logger.info("Imputed %d missing values in '%s' with median=%.3f", n_missing, col, median_val)

        for col in NOMINAL_COLUMNS + list(ORDINAL_MAPPINGS.keys()):
            if col in df.columns and df[col].isna().any():
                mode_val = df[col].mode(dropna=True)
                mode_val = mode_val.iloc[0] if not mode_val.empty else "Unknown"
                n_missing = df[col].isna().sum()
                df[col] = df[col].fillna(mode_val)
                logger.info("Imputed %d missing values in '%s' with mode='%s'", n_missing, col, mode_val)

        return df

    def clip_outliers(self, df: pd.DataFrame, fit: bool) -> pd.DataFrame:
        """
        Clip numeric outliers using the IQR method.

        When ``fit`` is True, IQR bounds are computed from the given data and
        stored in ``self.artifacts.clip_bounds``. When False, previously
        fitted bounds are applied (inference / test-time behaviour).
        """
        df = df.copy()
        for col in NUMERIC_COLUMNS:
            if col not in df.columns:
                continue
            if fit:
                q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                self.artifacts.clip_bounds[col] = (lower, upper)
            else:
                lower, upper = self.artifacts.clip_bounds.get(col, (-np.inf, np.inf))
            n_clipped = ((df[col] < lower) | (df[col] > upper)).sum()
            df[col] = df[col].clip(lower=lower, upper=upper)
            if n_clipped:
                logger.info("Clipped %d outliers in '%s' to [%.2f, %.2f]", n_clipped, col, lower, upper)
        return df

    @staticmethod
    def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create additional ratio/interaction features with business meaning."""
        df = df.copy()
        df["Lead_Time_Deviation"] = df["Lead_Time"] - df["Expected_Lead_Time"]
        df["Lead_Time_Deviation_Ratio"] = df["Lead_Time_Deviation"] / (df["Expected_Lead_Time"] + 1e-3)
        df["Risk_Composite_Index"] = (
            df["Weather_Severity"] + df["Port_Congestion"] + df["Route_Risk"] + df["Geopolitical_Risk"]
        ) / 4.0
        df["Cost_Per_Kg"] = df["Transportation_Cost"] / (df["Shipment_Weight"] + 1e-3)
        df["Supplier_Reliability_Score"] = (
            df["Supplier_Rating"] / 5.0 * 0.5 + df["Supplier_OnTime_Rate"] * 0.5
        )
        logger.info("Engineered 5 additional derived features.")
        return df

    def encode_ordinal(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply explicit ordinal mappings to ordered categorical columns."""
        df = df.copy()
        for col, mapping in ORDINAL_MAPPINGS.items():
            if col in df.columns:
                df[col] = df[col].map(mapping).fillna(-1).astype(int)
        return df

    def encode_nominal(self, df: pd.DataFrame, fit: bool) -> pd.DataFrame:
        """One-hot encode nominal categorical columns."""
        present_cols = [c for c in NOMINAL_COLUMNS if c in df.columns]
        df = pd.get_dummies(df, columns=present_cols, prefix=present_cols, dtype=int)
        return df

    def scale_features(self, df: pd.DataFrame, fit: bool) -> pd.DataFrame:
        """Standardize numeric feature columns using StandardScaler."""
        df = df.copy()
        engineered_numeric = [
            "Lead_Time_Deviation", "Lead_Time_Deviation_Ratio", "Risk_Composite_Index",
            "Cost_Per_Kg", "Supplier_Reliability_Score",
        ]
        scale_cols = [c for c in NUMERIC_COLUMNS + engineered_numeric if c in df.columns]

        if fit:
            self.artifacts.scaler = StandardScaler()
            df[scale_cols] = self.artifacts.scaler.fit_transform(df[scale_cols])
        else:
            df[scale_cols] = self.artifacts.scaler.transform(df[scale_cols])
        return df

    @staticmethod
    def select_features(df: pd.DataFrame, target: Optional[pd.Series] = None,
                         correlation_threshold: float = 0.97) -> pd.DataFrame:
        """
        Prune near-zero-variance and highly correlated redundant features.

        A correlation threshold of 0.97 removes near-duplicate numeric
        features while preserving distinct predictive signal.
        """
        # Drop zero-variance columns.
        variances = df.var(numeric_only=True)
        zero_var_cols = variances[variances == 0].index.tolist()
        if zero_var_cols:
            df = df.drop(columns=zero_var_cols)
            logger.info("Dropped %d zero-variance columns: %s", len(zero_var_cols), zero_var_cols)

        # Drop highly correlated redundant columns (keep the first of each pair).
        corr_matrix = df.corr(numeric_only=True).abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        to_drop = [col for col in upper.columns if any(upper[col] > correlation_threshold)]
        if to_drop:
            df = df.drop(columns=to_drop)
            logger.info("Dropped %d highly correlated columns (>%.2f): %s",
                        len(to_drop), correlation_threshold, to_drop)
        return df

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit the pipeline on training data and return the transformed frame."""
        logger.info("Starting fit_transform on %d rows.", len(df))
        self.validate_schema(df)

        df = self.remove_duplicates(df)
        df = self.handle_missing_values(df)
        df = self.clip_outliers(df, fit=True)
        df = self.engineer_features(df)
        df = self.encode_ordinal(df)
        df = self.encode_nominal(df, fit=True)
        df = self.select_features(df)
        df = self.scale_features(df, fit=True)

        drop_cols = [c for c in ID_AND_LEAKAGE_COLUMNS if c in df.columns]
        df = df.drop(columns=drop_cols)

        self.artifacts.feature_columns = [c for c in df.columns if c != TARGET_COLUMN]
        self._is_fitted = True
        logger.info("fit_transform complete. Final feature count: %d", len(self.artifacts.feature_columns))
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply a previously fitted pipeline to new (validation/test/inference) data."""
        if not self._is_fitted:
            raise RuntimeError("Pipeline must be fit_transform'ed before calling transform().")

        df = self.handle_missing_values(df)
        df = self.clip_outliers(df, fit=False)
        df = self.engineer_features(df)
        df = self.encode_ordinal(df)
        df = self.encode_nominal(df, fit=False)

        # Align columns to the fitted one-hot schema (handles unseen
        # categories at inference time gracefully).
        target_present = TARGET_COLUMN in df.columns
        target_series = df[TARGET_COLUMN] if target_present else None

        drop_cols = [c for c in ID_AND_LEAKAGE_COLUMNS if c in df.columns]
        df = df.drop(columns=drop_cols + ([TARGET_COLUMN] if target_present else []))
        df = df.reindex(columns=self.artifacts.feature_columns, fill_value=0)

        df = self.scale_features(df, fit=False)

        if target_present:
            df[TARGET_COLUMN] = target_series.values
        return df

    def split(self, df: pd.DataFrame, test_size: float = 0.2):
        """Perform a stratified train/test split on the target column."""
        X = df[self.artifacts.feature_columns]
        y = df[TARGET_COLUMN]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=RANDOM_SEED, stratify=y
        )
        logger.info(
            "Train/test split complete. Train=%d, Test=%d, Train positive rate=%.3f, Test positive rate=%.3f",
            len(X_train), len(X_test), y_train.mean(), y_test.mean(),
        )
        return X_train, X_test, y_train, y_test
