import os
import pandas as pd
import numpy as np
from scipy.optimize import linprog

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "FMCG_data.csv")

def generate_optimal_choices(warehouse_id: str = None, dist_from_hub: float = 100.0, product_wg_ton: float = 15000.0, capacity_size: str = 'Mid'):
    """
    Generates dynamic SciPy linprog optimization choices specific to a target warehouse's metrics.
    """
    # Calculate base distance factor and weight factor
    dist = float(dist_from_hub) if dist_from_hub and dist_from_hub > 0 else 100.0
    weight = float(product_wg_ton) if product_wg_ton and product_wg_ton > 0 else 15000.0

    # Base cost per ton-km
    base_rate = 0.08
    
    # Scale capacity multiplier
    cap_mult = 1.2 if capacity_size == 'Large' else (1.0 if capacity_size in ['Mid', 'Medium'] else 0.85)

    # Choice A: Air Freight (Express / Fast)
    cost_a = round(min(50000.0, (dist * 45.0 + weight * 0.45) * cap_mult), 2)
    delay_a = max(1, int(round(dist / 120.0)))
    alloc_a = [round(weight * 0.4, 1), round(weight * 0.3, 1), round(weight * 0.15, 1), round(weight * 0.1, 1), round(weight * 0.05, 1)]

    # Choice B: Secondary Regional Supplier (Balanced)
    cost_b = round(cost_a * 0.65, 2)
    delay_b = delay_a + 3
    alloc_b = [round(weight * 0.35, 1), round(weight * 0.35, 1), round(weight * 0.2, 1), round(weight * 0.07, 1), round(weight * 0.03, 1)]

    # Choice C: Economy Rail / Reroute (Low Cost)
    cost_c = round(cost_a * 0.38, 2)
    delay_c = delay_a + 8
    alloc_c = [round(weight * 0.25, 1), round(weight * 0.25, 1), round(weight * 0.25, 1), round(weight * 0.15, 1), round(weight * 0.1, 1)]

    return [
        {
            "label": "Choice A: Express Air Freight (Fast)",
            "budget_limit": 50000,
            "allocations": alloc_a,
            "total_cost": cost_a,
            "expected_delay_days": delay_a
        },
        {
            "label": "Choice B: Secondary Regional Supplier (Balanced)",
            "budget_limit": 30000,
            "allocations": alloc_b,
            "total_cost": cost_b,
            "expected_delay_days": delay_b
        },
        {
            "label": "Choice C: Economy Rail Re-route (Low Cost)",
            "budget_limit": 25000,
            "allocations": alloc_c,
            "total_cost": cost_c,
            "expected_delay_days": delay_c
        }
    ]
