# SupplyPrescript — Week 1: Predictive Analytics Engine

**Closed-Loop Prescriptive Analytics for Intelligent Supply Chain Decision Support**

This repository contains the Week-1 deliverable of SupplyPrescript: a production-grade
machine learning pipeline that predicts the probability a shipment will be delayed,
`P(Delay | X)`, using an XGBoost classifier trained on shipment, supplier, logistics,
and macro-risk features.

Later weeks will add a prescriptive optimization layer (recommended corrective actions)
on top of this predictive engine, served via FastAPI and backed by PostgreSQL.

---

## 1. Project Architecture

```
SupplyPrescript/
│
├── engine/                        # Serialized model + preprocessing artifacts
│   ├── xgboost_model.joblib       # Trained XGBoost classifier
│   ├── preprocessing_pipeline.pkl # Fitted PreprocessingPipeline (full object)
│   ├── feature_columns.pkl        # Ordered list of final model feature names
│   ├── label_encoders.pkl         # Ordinal category -> integer mappings
│   └── train_test_split.pkl       # Held-out test split (for evaluate_model.py)
│
├── dataset/
│   └── supply_chain_mock.csv      # Synthetic 20k+ row supply chain dataset
│
├── notebooks/                     # Reserved for exploratory analysis
│
├── scripts/
│   ├── generate_dataset.py        # Synthetic dataset generator
│   ├── preprocessing.py           # Reusable preprocessing/feature-engineering pipeline
│   ├── train_model.py             # Training + hyperparameter tuning + serialization
│   ├── evaluate_model.py          # Metrics, plots, SHAP explainability
│   └── predict.py                 # CLI + importable inference module
│
├── reports/                       # Generated evaluation artifacts (plots, metrics.json)
│
├── requirements.txt
└── README.md
```

### Pipeline flow

```
generate_dataset.py  -->  dataset/supply_chain_mock.csv
                              │
                              ▼
                     preprocessing.py (imported by train_model.py)
                              │
                              ▼
train_model.py --> RandomizedSearchCV (Stratified 5-Fold) --> engine/*.joblib, *.pkl
                              │
                              ▼
evaluate_model.py --> reports/*.png, reports/metrics.json, classification_report.txt
                              │
                              ▼
predict.py --> ShipmentDelayPredictor (CLI or importable for future FastAPI service)
```

---

## 2. Dataset Generation (`scripts/generate_dataset.py`)

Generates **20,100 rows** (20,000 base + injected duplicates) of synthetic but
business-realistic supply chain data across 45+ columns spanning supplier
attributes, logistics operations, shipment characteristics, macro/geopolitical
risk, and calendar features.

Key design choices:

- **Non-random target**: `Delay` is sampled from a logistic risk function of
  the generated features (lead-time deviation, weather severity, port
  congestion, route/geopolitical risk, supplier reliability, holiday impact,
  etc.), so the label carries genuine, learnable signal rather than noise.
- **Realistic data quality issues**: ~2–4% missing values injected into six
  operationally-plausible columns, plus a small number of duplicate rows —
  giving the preprocessing pipeline real work to do.
- **Reproducibility**: all sampling uses `numpy.random.default_rng(42)`.

Run:
```bash
python scripts/generate_dataset.py
```

---

## 3. Data Preprocessing & Feature Engineering (`scripts/preprocessing.py`)

Implemented as a single `PreprocessingPipeline` class with strict
`fit_transform` (train) / `transform` (test & inference) separation to avoid
data leakage. Steps:

1. **Schema validation** — fails fast with a clear `DataValidationError` if
   required columns are missing.
2. **Duplicate removal** — exact-row de-duplication.
3. **Missing value handling** — median imputation for numeric columns, mode
   imputation for categoricals.
4. **Outlier handling** — IQR-based clipping, bounds fit on training data and
   reused at inference time.
5. **Feature engineering** — 5 derived features: `Lead_Time_Deviation`,
   `Lead_Time_Deviation_Ratio`, `Risk_Composite_Index`, `Cost_Per_Kg`,
   `Supplier_Reliability_Score`.
6. **Encoding**:
   - Ordinal (`Supplier_Risk`, `Order_Priority`, `Production_Status`) — explicit
     ordinal integer mapping.
   - Nominal (country, carrier, warehouse, etc.) — one-hot encoding.
7. **Feature scaling** — `StandardScaler` fit on numeric + engineered columns.
8. **Feature selection** — drops zero-variance columns and prunes columns with
   pairwise correlation > 0.97 to reduce redundancy.
9. **Train/test split** — stratified 80/20 split, `random_state=42`.

The entire fitted pipeline (encoders, clip bounds, scaler, final feature
column list) is serialized as a single object to `engine/preprocessing_pipeline.pkl`,
guaranteeing train/serve consistency for Week-2 API integration.

---

## 4. Model Training & Hyperparameter Tuning (`scripts/train_model.py`)

- **Algorithm**: `XGBClassifier` (`objective="binary:logistic"`, `eval_metric="auc"`,
  `tree_method="hist"`).
- **Class imbalance handling**: `scale_pos_weight` computed from the training
  split's class ratio.
- **Tuning**: `RandomizedSearchCV` (30 candidates) over `learning_rate`,
  `max_depth`, `n_estimators`, `subsample`, `colsample_bytree`, `gamma`,
  `min_child_weight`, scored on ROC AUC with **Stratified 5-Fold** cross
  validation (`random_state=42` throughout).
- **Serialization**: best estimator + all preprocessing artifacts saved via
  `joblib` to `engine/`.

Run:
```bash
python scripts/train_model.py
```

Optional environment variable `SP_SEARCH_ITER` controls the number of
RandomizedSearchCV candidates (default `30`) for faster iteration during
development.

---

## 5. Model Evaluation & Explainability (`scripts/evaluate_model.py`)

Loads the serialized model and held-out test split and produces:

- Accuracy, Precision, Recall, F1, ROC AUC → `reports/metrics.json`
- Full `classification_report` → `reports/classification_report.txt`
- Confusion matrix → `reports/confusion_matrix.png`
- ROC curve → `reports/roc_curve.png`
- Precision-Recall curve → `reports/precision_recall_curve.png`
- XGBoost native feature importance (top 20) → `reports/feature_importance.png`
- **SHAP summary (beeswarm) plot** → `reports/shap_summary.png`
- **SHAP bar plot** (mean |SHAP value|) → `reports/shap_bar.png`

Run:
```bash
python scripts/evaluate_model.py
```

### Target performance

| Metric   | Target | 
|----------|--------|
| Accuracy | > 0.90 |
| ROC AUC  | > 0.92 |

Actual achieved values are written to `reports/metrics.json` after each
training/evaluation cycle — see that file for the current run's results.

---

## 6. Prediction / Inference (`scripts/predict.py`)

Exposes `ShipmentDelayPredictor`, a small class that loads the serialized
pipeline + model once and exposes `.predict(raw_df)`, returning
`Delay_Probability` and `Delay_Prediction` for each row. This class is the
intended integration point for the Week-2 FastAPI service (`POST /predict`).

CLI usage:
```bash
python scripts/predict.py --input dataset/new_shipments.csv --output predictions.csv
```

Library usage:
```python
from scripts.predict import ShipmentDelayPredictor

predictor = ShipmentDelayPredictor()
result_df = predictor.predict(new_shipments_df)
```

---

## 7. Coding Standards

- PEP-8 compliant, fully modular, docstrings on every public function/class.
- `logging` used throughout (no `print()` in library code).
- Explicit custom exceptions (`DataValidationError`, `ModelTrainingError`,
  `ModelEvaluationError`, `PredictionError`) with descriptive messages.
- Random seed fixed at `42` everywhere randomness is involved, for full
  reproducibility.

---

## 8. Setup

```bash
pip install -r requirements.txt

python scripts/generate_dataset.py
python scripts/train_model.py
python scripts/evaluate_model.py
```

---

## 9. Roadmap (beyond Week 1)

- **Week 2**: FastAPI service wrapping `ShipmentDelayPredictor` (`/predict`,
  `/health`, `/model-info` endpoints), PostgreSQL persistence of predictions.
- **Week 3+**: Prescriptive optimization layer (mathematical optimization over
  recommended corrective actions — e.g., carrier reassignment, expedited
  shipping, safety-stock adjustment) conditioned on the Week-1 delay
  probability, exposed to a React/Retool operations dashboard.
