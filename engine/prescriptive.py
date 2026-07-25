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
    # Objective: Minimize cost = sum(cost_i * x_i)
    c = df['Shipping_Cost_Per_Unit'].values
    
    # Constraint 1: Capacity bound
    bounds = [(0, cap) for cap in df['Capacity']]
    
    # Constraint 2: Budget (sum(cost_i * x_i) <= total_budget)
    A_ub = [c]
    b_ub = [total_budget]
    
    # Constraint 3: Demand (sum(x_i) >= total_demand) 
    total_demand = df['Demand'].sum()
    A_ub.append([-1] * len(df)) # -sum(x_i) <= -total_demand
    b_ub.append(-total_demand)
    
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    
    if result.success:
        return result.x.tolist()
    else:
        return None

def generate_optimal_choices(budgets: list = [50000, 30000, 25000]):
    """Generates 3 choices based on different budget constraints using the CSV data."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")
        
    df = pd.read_csv(DATA_PATH)
    choices = []
    labels = ['Choice A (High Budget)', 'Choice B (Medium Budget)', 'Choice C (Low Budget)']
    
    for label, budget in zip(labels, budgets):
        sol = optimize_shipment(df, budget)
        if sol is not None:
            choices.append({
                "label": label,
                "budget_limit": budget,
                "allocations": [round(x, 2) for x in sol],
                "total_cost": round(sum(df['Shipping_Cost_Per_Unit'].values * np.array(sol)), 2)
            })
    return choices
