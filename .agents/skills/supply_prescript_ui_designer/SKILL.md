---
name: supply-prescript-ui-designer
description: Guides the generation and coding of the React UI frontend for SupplyPrescript using clean CSS and the backend APIs.
---

# SupplyPrescript UI Designer & Frontend Guide

This skill provides coding instructions, design tokens, and components structure for building the **SupplyPrescript React Dashboard** (Vite + React).

---

## 🎨 Design Theme & Tokens

To create a premium look, use the following CSS variables and styles:

*   **Background:** Slate Dark (`#0f172a` / `#1e293b`)
*   **Cards:** Semi-transparent glassmorphism with light borders (`rgba(255,255,255,0.05)`).
*   **Accents:**
    *   *Normal / Optimal:* Emerald Green (`#10b981`)
    *   *Warning / Delayed:* Rose Red (`#f43f5e`) or Amber (`#f59e0b`)
*   **Typography:** Google Font Inter or Outfit.

---

## 🏗️ React Component Structure

Build the React application inside the `frontend/src` directory with these components:

```text
frontend/src/
├── App.jsx             # Main dashboard shell, controls tabs (Monitor vs. Outcomes)
├── index.css           # Core styling and theme configuration
├── components/
│   ├── Header.jsx      # status connection & title
│   ├── MonitorTab.jsx  # Warehouse table, search, filters
│   ├── Drawer.jsx      # Slide-out prescriptive action drawer (options A/B/C)
│   └── OutcomesTab.jsx # Form to log actual decision outcomes
```

---

## 📡 API Call Blueprints

Use `fetch` or `axios` to fetch data from the FastAPI server (`http://localhost:8000`).

### 1. Load Warehouses (Paginated)
```javascript
const fetchWarehouses = async (page = 0, limit = 50) => {
  const skip = page * limit;
  const res = await fetch(`http://localhost:8000/warehouses?skip=${skip}&limit=${limit}`);
  const data = await res.json();
  return data;
};
```

### 2. Execute Decision (Write-Back)
```javascript
const executeDecision = async (warehouseId, optionLabel, cost, delayDays) => {
  const res = await fetch('http://localhost:8000/execute-decision', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      warehouse_id: warehouseId,
      selected_option: optionLabel,
      prescribed_cost: parseFloat(cost),
      expected_delay_days: parseInt(delayDays)
    })
  });
  return res.json();
};
```

### 3. Log Outcome (Closed-Loop)
```javascript
const logOutcome = async (decisionId, actualCost, actualDelayDays) => {
  const res = await fetch('http://localhost:8000/log-outcome', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      decision_id: parseInt(decisionId),
      actual_cost: parseFloat(actualCost),
      actual_delay_days: parseInt(actualDelayDays)
    })
  });
  return res.json();
};
```
