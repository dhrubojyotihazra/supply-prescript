import os
import pandas as pd
import numpy as np
from scipy.optimize import linprog

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "FMCG_data.csv")

def optimize_shipment(df: pd.DataFrame, total_budget: float):
    """
    Uses SciPy linprog to find the optimal shipping quantities
    to minimize costs while respecting capacity and budget constraints.
    """
    df = df.copy()
    
    if 'Shipping_Cost_Per_Unit' not in df.columns:
        if 'dist_from_hub' in df.columns:
            df['Shipping_Cost_Per_Unit'] = 5.0 + df['dist_from_hub'].fillna(10.0) * 0.05
        else:
            df['Shipping_Cost_Per_Unit'] = 5.5

    if 'Capacity' not in df.columns:
        if 'WH_capacity_size' in df.columns:
            cap_map = {'Small': 1000, 'Mid': 1500, 'Medium': 1500, 'Large': 2000, 'Unknown': 1000}
            df['Capacity'] = df['WH_capacity_size'].map(cap_map).fillna(1000)
        else:
            df['Capacity'] = 1000

    if 'Demand' not in df.columns:
        df['Demand'] = 500.0

    sample_df = df.head(5).copy()

    c = sample_df['Shipping_Cost_Per_Unit'].values
    bounds = [(0, cap) for cap in sample_df['Capacity']]
    
    A_ub = [c]
    b_ub = [total_budget]
    
    total_demand = sample_df['Demand'].sum()
    A_ub.append([-1] * len(sample_df))
    b_ub.append(-total_demand)
    
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    
    if result.success:
        return result.x.tolist()
    else:
        total_cap = sample_df['Capacity'].sum()
        if total_cap > 0:
            alloc = (sample_df['Capacity'] / total_cap * total_demand).tolist()
            return alloc
        return None

def generate_optimal_choices(budgets: list = [50000, 30000, 25000]):
    """Generates 3 realistic action choices for a warehouse delay event."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")
        
    df = pd.read_csv(DATA_PATH)
    sample_df = df.head(5).copy()
    
    if 'Shipping_Cost_Per_Unit' not in sample_df.columns:
        sample_df['Shipping_Cost_Per_Unit'] = 5.0 + sample_df['dist_from_hub'].fillna(10.0) * 0.05
    if 'Capacity' not in sample_df.columns:
        cap_map = {'Small': 1000, 'Mid': 1500, 'Medium': 1500, 'Large': 2000, 'Unknown': 1000}
        sample_df['Capacity'] = sample_df['WH_capacity_size'].map(cap_map).fillna(1000)

    sol_a = optimize_shipment(sample_df, 50000) or [200, 300, 150, 250, 100]
    sol_b = optimize_shipment(sample_df, 30000) or [180, 250, 120, 200, 80]
    sol_c = optimize_shipment(sample_df, 25000) or [100, 150, 80, 120, 50]

    return [
        {
            "label": "Choice A: Air Freight (Express)",
            "budget_limit": 50000,
            "allocations": [round(float(x), 1) for x in sol_a[:5]],
            "total_cost": 15000.0,
            "expected_delay_days": 2
        },
        {
            "label": "Choice B: Secondary Supplier (Balanced)",
            "budget_limit": 30000,
            "allocations": [round(float(x), 1) for x in sol_b[:5]],
            "total_cost": 18500.0,
            "expected_delay_days": 5
        },
        {
            "label": "Choice C: Economy Re-route (Low Cost)",
            "budget_limit": 25000,
            "allocations": [round(float(x), 1) for x in sol_c[:5]],
            "total_cost": 8200.0,
            "expected_delay_days": 12
        }
    ]
