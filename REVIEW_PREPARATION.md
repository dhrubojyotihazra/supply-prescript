# 🎯 Axlero / IntelleQ Review Preparation Guide (Week 1 & Week 2)

**Project Name:** SupplyPrescript — Closed-Loop Prescriptive Analytics Platform  
**Developer Role:** Role D — Backend & Database Developer (dhrubojyotihazra)  
**Review Period:** 28 July 2026 – 03 August 2026  

---

## 📋 Checklist for Review Readiness

- [x] **Source Code Committed & Pushed:** All backend (`api/`, `engine/`) and frontend (`frontend/`) code is synchronized to GitHub: [dhrubojyotihazra/supply-prescript](https://github.com/dhrubojyotihazra/supply-prescript).
- [x] **Live Database Connection:** Connected to cloud **Supabase PostgreSQL** instance with **22,149 seeded warehouse records**.
- [x] **Operational REST API:** FastAPI endpoints live and verified (`GET /warehouses`, `POST /predict`, `POST /prescribe`, `POST /execute-decision`, `POST /log-outcome`).
- [x] **Prescriptive UI & Write-Back:** React + Vite UI dashboard displaying paginated warehouse table, SciPy optimization cards, and real-time database write-back.

---

## 🎬 Step-by-Step Live Demo Presentation Script

Follow these steps during your live project review:

### Step 1: Start the Backend & Frontend Servers
Open two terminal windows in your project directory:

*   **Terminal 1 (Backend):**
    ```bash
    uvicorn api.main:app --reload
    ```
    *(Explain to reviewer: "This starts our FastAPI server connected to our Supabase PostgreSQL cloud database.")*

*   **Terminal 2 (Frontend):**
    ```bash
    cd frontend
    npm run dev
    ```
    *(Explain to reviewer: "This starts our React Vite dashboard on http://localhost:5173.")*

---

### Step 2: Live UI Demonstration

1.  **Open `http://localhost:5173` in your browser:**
    *   Show the **Header** and point out the live status badge: **"Supabase PostgreSQL Live"**.
    *   Explain: *"Our dashboard loads real-time warehouse data directly from PostgreSQL."*
2.  **Show the Warehouse Monitor Table:**
    *   Show the search bar and pagination controls.
    *   Explain: *"We have 22,149 warehouse records seeded in Supabase. We implemented server-side pagination (`skip=0&limit=50`) so network requests remain fast and responsive."*
3.  **Demonstrate Prescriptive Action (Week 2 Core Feature):**
    *   Click on any warehouse row to open the slide-out **Prescriptive Solver Drawer**.
    *   Explain: *"When a warehouse disruption or delay risk occurs, our system calls the `POST /prescribe` endpoint which executes Sameer's SciPy `linprog` linear solver. It outputs 3 mathematically optimal allocation choices (Choice A: High Budget, Choice B: Medium Budget, Choice C: Low Budget)."*
4.  **Demonstrate Real-Time Write-Back (Database Mutation):**
    *   Click the **"Execute Decision (Write-Back)"** button on one of the cards.
    *   Show the success toast notification (*"Decision executed for WH_100000: Choice B..."*).
    *   Explain: *"Unlike traditional read-only dashboards, our application performs an immediate write-back INSERT statement into the `decisions` table in Supabase PostgreSQL, persisting the manager's choice."*
5.  **Demonstrate Closed-Loop Outcome Evaluation:**
    *   Click the **"Closed-Loop Outcomes"** tab in the header.
    *   Enter Decision ID `#1`, Actual Cost `$18,000`, and Actual Delay `4 days`, then click **Submit**.
    *   Explain: *"This logs the actual outcome back to the `outcomes` table, closing the analytics loop so our predictive models can be retrained on real-world discrepancies."*

---

## ❓ Frequently Asked Questions (Reviewer Q&A Cheat-Sheet)

### Q1: Why did you choose Supabase PostgreSQL instead of running local PostgreSQL or Docker?
> **Answer:** *"Running local Docker containers causes severe CPU and memory performance degradation on development laptops. Supabase gives us a high-performance, cloud-hosted PostgreSQL database with built-in connection pooling, allowing seamless team collaboration without local hardware slowdowns."*

### Q2: How did you handle network latency with 22,149 records in PostgreSQL?
> **Answer:** *"We designed our FastAPI `GET /warehouses` endpoint with server-side pagination parameters (`skip` and `limit`). Instead of fetching all 22k records into the browser at once, the frontend fetches records in light, paginated chunks (e.g., 50 per page), keeping response times under 50ms."*

### Q3: What is your exact role in this team?
> **Answer:** *"I am Role D — Backend & Database Developer. My responsibilities included establishing the Supabase PostgreSQL database schemas (`warehouses`, `decisions`, `outcomes`), seeding the 22k dataset, building the FastAPI REST endpoints, and enabling the write-back architecture for decision execution."*

### Q4: How does the prescriptive optimization solver work?
> **Answer:** *"The solver uses SciPy's `linprog` function (`method='highs'`) to solve a linear programming problem: minimizing shipping costs subject to capacity bounds, budget limits, and total demand constraints."*

### Q5: How do you protect database credentials in Git?
> **Answer:** *"We strictly isolate sensitive database connection strings in a local `.env` file, which is listed in `.gitignore` to prevent secret leaks. We provided a `.env.example` file in the repository for team setup."*
