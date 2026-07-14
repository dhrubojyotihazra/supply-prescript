# Team Roles & Daily Deadlines

This document defines the team division, roles, and the daily deadline schedule for **Week 1** of the SupplyPrescript project.

---

## 👥 Team Division & Roles

### 🧠 Category 1: ML & Optimization Engine (2 Developers)
This team works on analyzing the `FMCG_data.csv` dataset, training the predictive model, and building the mathematical optimization logic.

*   **Role A: Lead ML Engineer** (Assigned: **DineshReddy-Gajjala**)
    *   **Focus:** Training the core XGBoost model to predict shipment delays and performance tuning.
*   **Role B: Feature Engineering & Optimization Prototyping** (Assigned: **karthikpuchaginjala**)
    *   **Focus:** Preprocessing `FMCG_data.csv`, feature engineering (nulls, category encoding), and coding the SciPy linear solver baseline.

---

### 💻 Category 2: Operational UI & Write-Back (3 Developers)
This team works on building the FastAPI backend server, setting up the database, building the dashboard, and connecting all modules together.

*   **Role C: Backend & Database Developer** (Assigned: **dhrubojyotihazra**)
    *   **Focus:** Database schema setup (storing predictions, decision logs, and outcomes) and building FastAPI endpoints for write-back.
*   **Role D: Frontend & Dashboard Developer** (Assigned: **Sameer0166**)
    *   **Focus:** Designing the Retool or React UI dashboard to show delay warnings, display recommendations, and handle user interactions.
*   **Role E: Integration & Quality Assurance Engineer** (Assigned: **ravichandranithin**)
    *   **Focus:** Connecting frontend UI elements to the FastAPI backend endpoints, testing the write-back pipeline, and validating the end-to-end data flow.

---

## 📅 Daily Deadline Schedule (Week 1)

### **Day 1: Setup & Initial Scaffolding**
*   **ML Team:** Load `FMCG_data.csv`, clean missing values, and output basic data visualizations (EDA).
*   **Operational Team:** 
    *   Initialize database (PostgreSQL/SQL) with tables for `warehouses`, `decisions`, and `outcomes`.
    *   Set up FastAPI folder structure and confirm server runs locally.
*   **Target by EOD:** Dataset prepared; empty database and baseline FastAPI server running.

### **Day 2: Core Logic & Initial API**
*   **ML Team:** Perform feature encoding on categorical columns and train a baseline XGBoost model.
*   **Operational Team:**
    *   Implement FastAPI endpoints: `/predict` (mock) and `/write-back` (saves decision to database).
    *   Scaffold the React/Retool UI layout.
*   **Target by EOD:** XGBoost baseline model saved as file; database write-back endpoints ready.

### **Day 3: Solver & UI Scaffolding**
*   **ML Team:** Implement the SciPy solver script to output 3 optimal choices (A, B, C) based on budget/capacity constraints.
*   **Operational Team:** Connect UI tables and cards to show warehouse statuses and action buttons.
*   **Target by EOD:** SciPy solver baseline complete; Frontend UI dashboard screens designed.

### **Day 4: Pipeline Integration**
*   **ML Team:** Pack XGBoost prediction and SciPy optimization into a clean python module.
*   **Operational Team:** Integrate the ML module into the FastAPI backend, connecting the frontend elements to the real backend database write-back flow.
*   **Target by EOD:** Integrated application where UI clicks trigger the solver and write-back to database.

### **Day 5: Testing & Review**
*   **All Teams:** Perform end-to-end simulation (delay alert -> showing options -> clicking an option -> updating database).
*   **Target by EOD:** Week 1 Demo ready.
