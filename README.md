# SupplyPrescript: Closed-Loop Prescriptive Analytics

**Domain:** Supply Chain Operations & Operations Research

---

## 📖 Overview

Predictive analytics (e.g., predicting a supply chain delay) are now standard, but they only tell you *what* will happen. The human operator still has to figure out *what to do*. Furthermore, standard dashboards don't learn; if an operator makes a decision, the system rarely tracks whether that decision actually worked.

**SupplyPrescript** bridges this gap. It integrates machine learning forecasts with a mathematical optimization solver to prescribe optimal actions, writes the operator's decision back to the database, tracks real-world outcomes, and retrains the predictive model based on actual performance (closing the loop).

### 💡 Use Case Example
A logistics manager is warned by the predictive model of an impending 14-day delay for microchips. Instead of stopping there, the **SupplyPrescript** engine runs a linear optimization algorithm and prescribes three mathematically optimal alternatives:
*   **Option A:** Pay \$15k for Air Freight.
*   **Option B:** Buy from a secondary supplier at a 10% premium.
*   **Option C:** Delay the final product launch.

The manager clicks **Option A** directly in the dashboard. The system writes this decision back to the operational database. Three weeks later, the system evaluates the outcome—learning that air freight actually cost \$18k—and adjusts its future optimization weights accordingly (Closed-Loop Analytics).

---

## 🛠️ Key Modules

*   **Predictive Model (XGBoost / LightGBM):** Predicts the probability and duration of supply chain disruptions based on historical lead times and warehouse operational attributes.
*   **Prescriptive Solver (SciPy / PuLP):** A mathematical optimization engine that calculates the absolute best business decisions subject to constraints (Budget, Time, Capacity).
*   **Write-Back Architecture (FastAPI & Supabase PostgreSQL):** A transactional pipeline allowing business users to insert operational decisions directly back into the data warehouse, closing the loop.
*   **Operational Dashboard (React / Retool):** An interactive interface where users review AI recommendations and execute decisions directly, replacing passive read-only BI reports.

---

## 📅 Week-Wise Development Plan

### 🚀 Week 1: Predictive Baseline & App Scaffolding [COMPLETED]
*   **ML & Optimization Engine (XGBoost/SciPy):** Trained baseline XGBoost model on `FMCG_data.csv` (achieving 87.99% validation accuracy) and saved to `engine/xgboost_model.joblib`.
*   **Operational UI & Write-Back (FastAPI/Supabase):** Set up backend structure (`api/`), established connection to Supabase PostgreSQL, created tables (`warehouses`, `decisions`, `outcomes`), and seeded 22,149 records.

### 📊 Week 2: Mathematical Optimization & Prescriptive UI/API [IN PROGRESS]
*   **ML & Optimization Engine:** Define business constraints (e.g., maximum budget, minimum inventory). Connect Sameer's SciPy `linprog` optimizer into a production service (`engine/prescriptive.py`) to generate optimal shipping allocations.
*   **Operational UI & Write-Back:** Build the `/prescribe` endpoint to output the optimal choices (A: High Budget, B: Medium Budget, C: Low Budget) with their cost/speed trade-offs. Create the Prescriptive UI card blueprints.

### 🔍 Mid-Project Review [UPCOMING]
*   **Optimization Audit:** Prove that the SciPy solver never recommends an action that violates the hard budget constraints defined in the code.
*   **Write-Back Check:** Ensure that clicking "Execute Decision" in the UI successfully performs an `INSERT` statement back into the operational database.

### 🔁 Week 3: Closed-Loop Evaluation & Feedback UI
*   **ML & Optimization Engine:** Write the evaluation script. Compare the predicted cost of the user's decision against the actual historical outcome stored in the database.
*   **Operational UI & Write-Back:** Build an analytics view showing the "Decision ROI"—tracking how often the AI's recommendations resulted in positive business outcomes.

### 🔄 Week 4: Continuous Learning & Polish
*   **ML & Optimization Engine:** Implement a pipeline where the discrepancies discovered in the Closed Loop automatically trigger a re-training of the XGBoost model.
*   **Operational UI & Write-Back:** Polish the workflow, ensuring the analyst is an active participant in an AI-driven workflow rather than a passive observer.

---

## 🌟 Common Architecture Features

*   **Agentic & Automated Workflows:** Replacing manual, human-in-the-loop BI analysis with agentic orchestration, self-healing data pipelines, and prescribed decision-making.
*   **Modern Data Architecture (2026 Standards):** Utilizing semantic layers and streaming ingestions to overcome the latency and governance limitations of legacy data warehouses.
*   **Write-Back and Closed-Loop Systems:** Moving away from read-only "dead" dashboards to bidirectional data flows, allowing user decisions to mutate the underlying databases and retrain models.
*   **Strict Governance & Observability:** Treating data quality and metric consistency as engineering requirements rather than business afterthoughts.
