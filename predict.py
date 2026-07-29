"""
predict.py
==========

SupplyPrescript - Week 1 Predictive Analytics Engine
Standalone / importable prediction module.

Loads the serialized preprocessing pipeline and trained XGBoost model to
produce P(Delay | X) for new shipment records. Designed to be imported
directly by a future FastAPI service layer (Week 2+), or run as a CLI
utility against a CSV of new shipments.

Usage
-----
    # As a CLI tool:
    python scripts/predict.py --input dataset/new_shipments.csv --output predictions.csv

    # As a library:
    from scripts.predict import ShipmentDelayPredictor
    predictor = ShipmentDelayPredictor()
    result_df = predictor.predict(raw_shipment_df)

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import joblib
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from preprocessing import PreprocessingPipeline  # noqa: E402  (kept for type reference / unpickling)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("predict")

ENGINE_DIR = "engine"
MODEL_PATH = os.path.join(ENGINE_DIR, "xgboost_model.joblib")
PREPROCESSING_PIPELINE_PATH = os.path.join(ENGINE_DIR, "preprocessing_pipeline.pkl")

DEFAULT_DELAY_THRESHOLD = 0.5  # Overridable; see reports/metrics.json for the
                                 # accuracy-optimal threshold found by evaluate_model.py.


class PredictionError(Exception):
    """Raised when a fatal error occurs during the prediction workflow."""


class ShipmentDelayPredictor:
    """
    Production inference wrapper around the trained SupplyPrescript delay
    model and its fitted preprocessing pipeline.

    This class is the intended integration point for the future FastAPI
    service layer: instantiate once at service startup, then call
    :meth:`predict` per incoming request/batch.
    """

    def __init__(self, model_path: str = MODEL_PATH, pipeline_path: str = PREPROCESSING_PIPELINE_PATH):
        self.model_path = model_path
        self.pipeline_path = pipeline_path
        self.model = None
        self.pipeline: PreprocessingPipeline | None = None
        self._load()

    def _load(self) -> None:
        """Load the serialized model and preprocessing pipeline."""
        if not os.path.exists(self.model_path):
            raise PredictionError(f"Model file not found at '{self.model_path}'.")
        if not os.path.exists(self.pipeline_path):
            raise PredictionError(f"Preprocessing pipeline not found at '{self.pipeline_path}'.")

        try:
            self.model = joblib.load(self.model_path)
            self.pipeline = joblib.load(self.pipeline_path)
        except Exception as exc:  # noqa: BLE001
            raise PredictionError(f"Failed to load model artifacts: {exc}") from exc

        logger.info("Loaded model from '%s' and pipeline from '%s'.", self.model_path, self.pipeline_path)

    def predict(self, raw_df: pd.DataFrame, threshold: float = DEFAULT_DELAY_THRESHOLD) -> pd.DataFrame:
        """
        Generate delay predictions for new shipment records.

        Parameters
        ----------
        raw_df : pd.DataFrame
            Raw shipment records with the same schema as the training data
            (target column ``Delay`` may be absent).
        threshold : float
            Probability threshold above which a shipment is classified as
            delayed. Defaults to 0.5.

        Returns
        -------
        pd.DataFrame
            A copy of the identifying columns (if present) plus
            ``Delay_Probability`` and ``Delay_Prediction``.
        """
        if raw_df.empty:
            raise PredictionError("Input dataframe is empty; nothing to predict.")

        try:
            processed = self.pipeline.transform(raw_df.copy())
        except Exception as exc:  # noqa: BLE001
            raise PredictionError(f"Preprocessing failed during inference: {exc}") from exc

        feature_cols = self.pipeline.artifacts.feature_columns
        X = processed[feature_cols]

        probabilities = self.model.predict_proba(X)[:, 1]
        predictions = (probabilities >= threshold).astype(int)

        result = pd.DataFrame(index=raw_df.index)
        if "Shipment_ID" in raw_df.columns:
            result["Shipment_ID"] = raw_df["Shipment_ID"].values
        result["Delay_Probability"] = probabilities.round(4)
        result["Delay_Prediction"] = predictions

        logger.info(
            "Generated %d predictions. Predicted delay rate: %.2f%%",
            len(result), predictions.mean() * 100,
        )
        return result


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for standalone CLI execution."""
    parser = argparse.ArgumentParser(
        description="Predict shipment delay probabilities using the trained SupplyPrescript model."
    )
    parser.add_argument("--input", required=True, help="Path to a CSV file of new shipment records.")
    parser.add_argument("--output", default="predictions.csv", help="Path to write predictions CSV.")
    parser.add_argument("--threshold", type=float, default=DEFAULT_DELAY_THRESHOLD,
                         help="Probability threshold for classifying a shipment as delayed.")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = _parse_args()

    if not os.path.exists(args.input):
        raise PredictionError(f"Input file not found: '{args.input}'")

    raw_df = pd.read_csv(args.input, parse_dates=["Order_Date"]) if "Order_Date" in pd.read_csv(
        args.input, nrows=0).columns else pd.read_csv(args.input)

    predictor = ShipmentDelayPredictor()
    results = predictor.predict(raw_df, threshold=args.threshold)
    results.to_csv(args.output, index=False)
    logger.info("Predictions written to '%s'.", args.output)


if __name__ == "__main__":
    main()
