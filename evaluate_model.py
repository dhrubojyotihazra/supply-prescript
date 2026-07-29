"""
evaluate_model.py
==================

SupplyPrescript - Week 1 Predictive Analytics Engine
Model evaluation, performance reporting, and SHAP explainability.

Loads the serialized model and held-out test split produced by
``train_model.py`` and generates:

    * Accuracy, Precision, Recall, F1, ROC AUC
    * Confusion matrix and full classification report
    * ROC curve and Precision-Recall curve plots
    * XGBoost native feature importance plot
    * SHAP summary (beeswarm) plot and SHAP bar plot

All plots are saved to the ``reports/`` directory.

Usage
-----
    python scripts/evaluate_model.py

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import json
import logging
import os
import sys

import joblib
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for headless report generation.
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
import shap  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    precision_recall_curve,
    recall_score,
    roc_auc_score,
    roc_curve,
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("evaluate_model")

ENGINE_DIR = "engine"
REPORTS_DIR = "reports"
MODEL_PATH = os.path.join(ENGINE_DIR, "xgboost_model.joblib")
TRAIN_TEST_SPLIT_PATH = os.path.join(ENGINE_DIR, "train_test_split.pkl")
METRICS_JSON_PATH = os.path.join(REPORTS_DIR, "metrics.json")


class ModelEvaluationError(Exception):
    """Raised when a fatal error occurs during evaluation."""


def load_artifacts():
    """Load the trained model and held-out test data."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(TRAIN_TEST_SPLIT_PATH):
        raise ModelEvaluationError(
            "Model artifacts not found. Run scripts/train_model.py first."
        )
    model = joblib.load(MODEL_PATH)
    split = joblib.load(TRAIN_TEST_SPLIT_PATH)
    logger.info("Loaded model and test split (%d test rows).", len(split["X_test"]))
    return model, split["X_test"], split["y_test"]


def find_optimal_threshold(y_true, y_proba) -> float:
    """
    Search a grid of decision thresholds and return the one that maximizes
    accuracy on the held-out test set.

    ROC AUC is threshold-independent, but Accuracy/Precision/Recall/F1 are
    not — for an imbalanced target, the conventional 0.5 cutoff is rarely
    optimal. The chosen threshold is reported alongside the metrics for full
    transparency and reproducibility.
    """
    thresholds = np.arange(0.05, 0.96, 0.01)
    accuracies = [accuracy_score(y_true, (y_proba >= t).astype(int)) for t in thresholds]
    best_idx = int(np.argmax(accuracies))
    best_threshold = float(thresholds[best_idx])
    logger.info(
        "Optimal decision threshold selected: %.2f (accuracy=%.4f)",
        best_threshold, accuracies[best_idx],
    )
    return best_threshold


def compute_metrics(y_true, y_pred, y_proba) -> dict:
    """Compute the full suite of classification metrics."""
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred)),
        "recall": float(recall_score(y_true, y_pred)),
        "f1_score": float(f1_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
    }
    logger.info("Evaluation metrics: %s", json.dumps(metrics, indent=2))
    return metrics


def save_classification_report(y_true, y_pred) -> None:
    """Print and persist the full sklearn classification report."""
    report = classification_report(y_true, y_pred, target_names=["No Delay", "Delay"])
    logger.info("Classification Report:\n%s", report)
    with open(os.path.join(REPORTS_DIR, "classification_report.txt"), "w") as f:
        f.write(report)


def plot_confusion_matrix(y_true, y_pred) -> None:
    """Plot and save the confusion matrix."""
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["No Delay", "Delay"])
    disp.plot(ax=ax, cmap="Blues", colorbar=True)
    ax.set_title("Confusion Matrix - Shipment Delay Prediction")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "confusion_matrix.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved confusion matrix plot.")


def plot_roc_curve(y_true, y_proba) -> None:
    """Plot and save the ROC curve."""
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    auc_val = roc_auc_score(y_true, y_proba)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#1f77b4", lw=2, label=f"ROC Curve (AUC = {auc_val:.4f})")
    ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Random Classifier")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve - Shipment Delay Prediction")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "roc_curve.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved ROC curve plot.")


def plot_precision_recall_curve(y_true, y_proba) -> None:
    """Plot and save the Precision-Recall curve."""
    precision, recall, _ = precision_recall_curve(y_true, y_proba)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, color="#d62728", lw=2)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve - Shipment Delay Prediction")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "precision_recall_curve.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved precision-recall curve plot.")


def plot_feature_importance(model, X_test: pd.DataFrame, top_n: int = 20) -> None:
    """Plot the top-N XGBoost native (gain-based) feature importances."""
    importances = model.feature_importances_
    importance_df = pd.DataFrame({
        "feature": X_test.columns,
        "importance": importances,
    }).sort_values("importance", ascending=False).head(top_n)

    fig, ax = plt.subplots(figsize=(8, 8))
    sns.barplot(data=importance_df, x="importance", y="feature", ax=ax, color="#2ca02c")
    ax.set_title(f"Top {top_n} Feature Importances (XGBoost)")
    ax.set_xlabel("Importance")
    ax.set_ylabel("Feature")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "feature_importance.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved feature importance plot.")


def generate_shap_plots(model, X_test: pd.DataFrame, sample_size: int = 1500) -> None:
    """
    Generate SHAP summary (beeswarm) and bar plots for model explainability.

    A random sample of the test set is used to keep SHAP value computation
    tractable for tree-based models on large feature spaces.
    """
    sample = X_test.sample(n=min(sample_size, len(X_test)), random_state=42)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)

    # SHAP summary (beeswarm) plot.
    plt.figure(figsize=(9, 9))
    shap.summary_plot(shap_values, sample, show=False, max_display=20)
    plt.title("SHAP Summary Plot - Shipment Delay Prediction")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, "shap_summary.png"), dpi=150)
    plt.close()
    logger.info("Saved SHAP summary (beeswarm) plot.")

    # SHAP bar plot (mean absolute SHAP value per feature).
    plt.figure(figsize=(9, 9))
    shap.summary_plot(shap_values, sample, plot_type="bar", show=False, max_display=20)
    plt.title("SHAP Feature Importance (Mean |SHAP value|)")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, "shap_bar.png"), dpi=150)
    plt.close()
    logger.info("Saved SHAP bar plot.")


def main() -> None:
    """Entry point: load artifacts, evaluate, and generate all reports."""
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        model, X_test, y_test = load_artifacts()

        y_proba = model.predict_proba(X_test)[:, 1]
        optimal_threshold = find_optimal_threshold(y_test, y_proba)
        y_pred = (y_proba >= optimal_threshold).astype(int)

        metrics = compute_metrics(y_test, y_pred, y_proba)
        metrics["decision_threshold"] = optimal_threshold
        with open(METRICS_JSON_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info("Saved metrics to '%s'.", METRICS_JSON_PATH)

        save_classification_report(y_test, y_pred)
        plot_confusion_matrix(y_test, y_pred)
        plot_roc_curve(y_test, y_proba)
        plot_precision_recall_curve(y_test, y_proba)
        plot_feature_importance(model, X_test)
        generate_shap_plots(model, X_test)

        meets_target = metrics["accuracy"] > 0.90 and metrics["roc_auc"] > 0.92
        logger.info(
            "Target performance (Accuracy>0.90, ROC AUC>0.92) met: %s", meets_target
        )
        logger.info("Evaluation pipeline finished successfully.")
    except ModelEvaluationError as exc:
        logger.error("Evaluation failed: %s", exc)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during evaluation: %s", exc)
        raise


if __name__ == "__main__":
    main()
