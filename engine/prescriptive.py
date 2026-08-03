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
    
    # Ensure column compatibility between Kaggle dataset & mock schema
    if 'Shipping_Cost_Per_Unit' not in df.columns:
        if 'dist_from_hub' in df.columns:
            df['Shipping_Cost_Per_Unit'] = 5.0 + df['dist_from_hub'].fillna(10.0) * 0.05
        else:
            df['Shipping_Cost_Per_Unit'] = 5.5

    if 'Capacity' not in df.columns:
        if 'WH_capacity_size' in df.columns:
            cap_map = {'Small': 1000, 'Mid': 1500, 'Medium': 1500, 'Large': 2000, 'Unknown': 1000}
            df['Capacity'] = df['WH_capacity_size'].map(cap_map).fillna(1000)
        elif 'product_wg_ton' in df.columns:
            df['Capacity'] = df['product_wg_ton'].fillna(1000)
        else:
            df['Capacity'] = 1000

    if 'Demand' not in df.columns:
        if 'product_wg_ton' in df.columns:
            df['Demand'] = (df['product_wg_ton'].fillna(500) * 0.4).clip(lower=100)
        else:
            df['Demand'] = 500.0

    # Limit to top candidate warehouses for fast optimization
    sample_df = df.head(10).copy()

    # Objective: Minimize cost = sum(cost_i * x_i)
    c = sample_df['Shipping_Cost_Per_Unit'].values
    
    # Constraint 1: Capacity bound
    bounds = [(0, cap) for cap in sample_df['Capacity']]
    
    # Constraint 2: Budget (sum(cost_i * x_i) <= total_budget)
    A_ub = [c]
    b_ub = [total_budget]
    
    # Constraint 3: Demand (sum(x_i) >= total_demand) 
    total_demand = sample_df['Demand'].sum()
    A_ub.append([-1] * len(sample_df)) # -sum(x_i) <= -total_demand
    b_ub.append(-total_demand)
    
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    
    if result.success:
        return result.x.tolist()
    else:
        # Fallback to proportional allocation if budget is tight
        total_cap = sample_df['Capacity'].sum()
        if total_cap > 0:
            alloc = (sample_df['Capacity'] / total_cap * total_demand).tolist()
            return alloc
        return None

def generate_optimal_choices(budgets: list = [50000, 30000, 25000]):
    """Generates 3 choices based on different budget constraints using the CSV data."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")
        
    df = pd.read_csv(DATA_PATH)
    choices = []
    labels = ['Choice A (High Budget)', 'Choice B (Medium Budget)', 'Choice C (Low Budget)']
    
    # Prepare dynamic sample df
    sample_df = df.head(10).copy()
    if 'Shipping_Cost_Per_Unit' not in sample_df.columns:
        sample_df['Shipping_Cost_Per_Unit'] = 5.0 + sample_df['dist_from_hub'].fillna(10.0) * 0.05
    if 'Capacity' not in sample_df.columns:
        cap_map = {'Small': 1000, 'Mid': 1500, 'Medium': 1500, 'Large': 2000, 'Unknown': 1000}
        sample_df['Capacity'] = sample_df['WH_capacity_size'].map(cap_map).fillna(1000)
    if 'Demand' not in sample_df.columns:
        sample_df['Demand'] = (sample_df['product_wg_ton'].fillna(500) * 0.4).clip(lower=100)

    costs = sample_df['Shipping_Cost_Per_Unit'].values

    for label, budget in zip(labels, budgets):
        sol = optimize_shipment(sample_df, budget)
        if sol is not None:
            calc_cost = round(float(sum(costs * np.array(sol))), 2)
            choices.append({
                "label": label,
                "budget_limit": budget,
                "allocations": [round(float(x), 1) for x in sol[:5]],
                "total_cost": calc_cost
            })
    return choices
