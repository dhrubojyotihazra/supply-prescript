# SupplyPrescript: Closed-Loop Prescriptive Analytics

**Domain:** Supply Chain Operations & Operations Research  
**GitHub Repository:** [dhrubojyotihazra/supply-prescript](https://github.com/dhrubojyotihazra/supply-prescript)  

---

## 📖 Overview & Use Case

Predictive analytics (e.g., predicting a supply chain delay) are now standard, but they only tell you *what* will happen. The human operator still has to figure out *what to do*. Furthermore, standard dashboards don't learn; if an operator makes a decision, the system rarely tracks whether that decision actually worked.

**SupplyPrescript** bridges this gap. It integrates machine learning forecasts with a mathematical optimization solver to prescribe optimal actions, writes the operator's decision back to the database, tracks real-world outcomes, and retrains the predictive model based on actual performance (closing the loop).

### 💡 Use Case Example
A logistics manager is warned by the predictive model of an impending 14-day delay for microchips. Instead of stopping there, the **SupplyPrescript** engine runs a linear optimization algorithm and prescribes three mathematically optimal alternatives:
*   **Choice A:** Pay \$15k for Air Freight.
*   **Choice B:** Buy from a secondary supplier at a 10% premium.
*   **Choice C:** Delay the final product launch.

The manager clicks **Choice A** directly in the dashboard. The system writes this decision back to the operational database. Three weeks later, the system evaluates the outcome—learning that air freight actually cost \$18k—and adjusts its future optimization weights accordingly (Closed-Loop Analytics).

---

## 🏗️ Project Architecture & Directory Layout

```text
SupplyPrescript/
├── api/                           # FastAPI backend server & database connection
│   ├── database.py                # SQLAlchemy engine & Supabase connection
│   ├── main.py                    # REST API routes (/warehouses, /prescribe, /execute-decision)
│   ├── models.py                  # PostgreSQL ORM models (warehouses, decisions, outcomes)
│   └── schemas.py                 # Pydantic request/response validation schemas
│
├── engine/                        # Serialized ML models & optimization logic
│   ├── xgboost_model.joblib       # Trained XGBoost delay classifier (87.99% accuracy)
│   ├── predictive.py              # XGBoost risk prediction service
│   ├── prescriptive.py            # SciPy linprog optimization solver service
│   └── preprocessing_pipeline.pkl # Fitted preprocessing pipeline
│
├── frontend/                      # React + Vite UI Dashboard application
│   ├── src/
│   │   ├── components/            # Header, MonitorTab, Drawer, OutcomesTab
│   │   ├── App.jsx                # Main application shell
│   │   └── index.css              # Dark mode glassmorphic styling
│   └── package.json
│
├── data/                          # Dataset repository
│   ├── FMCG_data.csv              # Main 22,149-row supply chain dataset
│   └── supply_chain_mock.csv      # Synthetic ML training dataset
│
├── scripts/                       # Machine Learning & Synthetic Data Scripts
│   ├── generate_dataset.py        # Synthetic dataset generator
│   ├── preprocessing.py           # Feature engineering & missing value pipeline
│   ├── train_model.py             # XGBoost model training & hyperparameter tuning
│   ├── evaluate_model.py          # Model evaluation, SHAP explainability & ROC metrics
│   ├── predict.py                 # ML inference script
│   └── solver.py                  # Linear programming optimization solver
│
├── reports/                       # Generated evaluation plots & metric JSONs
│   ├── confusion_matrix.png
│   ├── roc_curve.png
│   ├── feature_importance.png
│   └── metrics.json
│
├── .agents/                       # Custom Workspace Skills & Instructions
│   └── skills/
│       ├── supply_prescript_spec/
│       └── supply_prescript_ui_designer/
│
├── REVIEW_PREPARATION.md          # Official Axlero/IntelleQ Review Presentation Guide
├── TEAM_EXPLAINER.md              # Team Roles, LaTeX math formulas, & Mermaid diagrams
├── seed_data.py                   # Supabase PostgreSQL database seeder script
├── requirements.txt               # Unified project python dependencies
└── README.md                      # Master project documentation
```

---

## 🛠️ Machine Learning Engine (`scripts/`)

The predictive engine uses an **XGBoost Classifier** trained on shipment, supplier, logistics, and macro-risk features:

1. **Synthetic Dataset Generation (`scripts/generate_dataset.py`):**
   Generates realistic supply chain data across 45+ columns spanning supplier attributes, logistics operations, port congestion, and weather risk.
2. **Data Preprocessing (`scripts/preprocessing.py`):**
   Implements a `PreprocessingPipeline` class with strict `fit_transform` (train) and `transform` (test/inference) separation to avoid data leakage.
3. **Model Training & Tuning (`scripts/train_model.py`):**
   Uses `RandomizedSearchCV` with 5-fold Stratified Cross-Validation to optimize hyperparameters. Achieves **87.99% validation accuracy**.
4. **Evaluation & Explainability (`scripts/evaluate_model.py`):**
   Generates confusion matrices, ROC curves, and SHAP feature importance plots saved to `reports/`.

---

## 📐 Mathematical Prescriptive Solver (`engine/prescriptive.py`)

When a delay risk is detected, the prescriptive engine runs a **SciPy Linear Programming (`linprog`) solver** to minimize total shipping costs subject to constraints:

$$\min_{x_1, \dots, x_n} \sum_{i=1}^{n} c_i \cdot x_i$$

**Subject to:**
1. **Capacity Bounds:** $0 \le x_i \le \text{Capacity}_i$
2. **Budget Constraint:** $\sum_{i=1}^{n} c_i \cdot x_i \le \text{Total Budget}$
3. **Demand Constraint:** $\sum_{i=1}^{n} x_i \ge \text{Total Demand}$

Outputs 3 action choices (**Choice A: High Budget/Fast**, **Choice B: Medium Budget/Balanced**, **Choice C: Low Budget/Economy**).

---

## 📅 Week-Wise Development Plan & Status

### 🚀 Week 1: Predictive Baseline & App Scaffolding [COMPLETED]
*   **ML Engine:** Trained baseline XGBoost model on `FMCG_data.csv` (87.99% accuracy) saved to `engine/xgboost_model.joblib`.
*   **Database & API:** Connected to Supabase PostgreSQL cloud database, created `warehouses`, `decisions`, and `outcomes` tables, and seeded 22,149 records.

### 📊 Week 2: Mathematical Optimization & Prescriptive UI/API [COMPLETED]
*   **Optimization Service:** Integrated SciPy `linprog` optimizer into `engine/prescriptive.py` and exposed `POST /prescribe` API.
*   **React Dashboard:** Built the dark-mode React UI (`frontend/`) with paginated table, prescriptive cards drawer, real-time database write-back, and outcome logger.

### 🔁 Week 3: Closed-Loop Evaluation & ROI Analytics [UPCOMING]
*   Compare predicted decision costs against actual real-world outcomes logged in the `outcomes` table.

---

## 🚀 How to Run the Project Locally

### 1. Start the FastAPI Backend
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```
*Backend runs on `http://127.0.0.1:8000` (Swagger Docs at `http://127.0.0.1:8000/docs`).*

### 2. Start the React Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
*Frontend runs on `http://localhost:5173`.*
