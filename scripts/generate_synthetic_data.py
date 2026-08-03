"""
generate_synthetic_data.py
---------------------------
Generates a realistic synthetic FMCG (Fast-Moving Consumer Goods) supply chain
dataset for SupplyPrescript Week-1 development, since a real FMCG_data.csv was
not available. The generator encodes real-world supply chain relationships
(e.g. supplier reliability -> delay probability, distance -> lead time,
weekday/holiday seasonality) so that the EDA, feature engineering and ML
modules produce meaningful, non-random signal.

Run:
    python generate_synthetic_data.py --rows 15000 --seed 42
Output:
    ../../data/FMCG_data.csv
"""

import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate(n_rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    suppliers = [f"SUP-{i:03d}" for i in range(1, 41)]
    supplier_reliability = {s: rng.beta(8, 2) for s in suppliers}  # most reliable, some poor
    supplier_region = {s: rng.choice(["North", "South", "East", "West", "Central"]) for s in suppliers}

    warehouses = [f"WH-{i:02d}" for i in range(1, 13)]
    warehouse_capacity = {w: int(rng.integers(5000, 50000)) for w in warehouses}
    warehouse_region = {w: rng.choice(["North", "South", "East", "West", "Central"]) for w in warehouses}

    products = [
        ("Beverages", 30), ("Snacks", 45), ("Personal Care", 60),
        ("Home Care", 90), ("Dairy", 7), ("Frozen Foods", 20),
        ("Confectionery", 120), ("Staples", 180),
    ]
    product_categories = [p[0] for p in products]
    shelf_life_map = dict(products)

    transport_modes = ["Road", "Rail", "Air", "Sea"]
    transport_base_days = {"Road": 3, "Rail": 5, "Air": 1, "Sea": 12}
    transport_cost_per_km = {"Road": 0.08, "Rail": 0.05, "Air": 0.45, "Sea": 0.02}

    customer_priorities = ["Standard", "High", "Critical"]

    start_date = datetime(2023, 1, 1)
    date_span_days = 730  # 2 years

    rows = []
    for i in range(n_rows):
        order_id = f"ORD-{100000 + i}"
        order_offset = int(rng.integers(0, date_span_days))
        order_date = start_date + timedelta(days=order_offset)

        supplier = rng.choice(suppliers)
        warehouse = rng.choice(warehouses)
        category = rng.choice(product_categories)
        mode = rng.choice(transport_modes, p=[0.5, 0.2, 0.1, 0.2])

        distance_km = float(rng.uniform(50, 3000))
        reliability = supplier_reliability[supplier]

        base_lead = transport_base_days[mode] + distance_km / 800
        # unreliable suppliers add variance and positive bias to lead time
        supplier_noise = rng.normal(loc=(1 - reliability) * 4, scale=1.2)
        weekday = order_date.weekday()
        weekend_penalty = 0.8 if weekday >= 5 else 0.0
        month = order_date.month
        holiday_indicator = 1 if month in (11, 12) else 0
        holiday_penalty = 1.5 if holiday_indicator else 0.0

        planned_lead_time = max(1, base_lead)
        actual_lead_time = max(1, base_lead + supplier_noise + weekend_penalty + holiday_penalty
                                + rng.normal(0, 0.8))

        delivery_date = order_date + timedelta(days=float(actual_lead_time))
        delay_days = actual_lead_time - planned_lead_time
        is_delayed = 1 if delay_days > 1.0 else 0

        order_quantity = int(rng.integers(50, 5000))
        unit_cost = float(rng.uniform(0.5, 25))
        shipping_cost = round(distance_km * transport_cost_per_km[mode] * (order_quantity / 500), 2)

        inventory_level = int(rng.integers(0, warehouse_capacity[warehouse]))
        reorder_point = int(warehouse_capacity[warehouse] * 0.15)

        customer_priority = rng.choice(customer_priorities, p=[0.6, 0.3, 0.1])

        # introduce some missingness and dirty data on purpose (realistic dataset)
        if rng.random() < 0.02:
            unit_cost = np.nan
        if rng.random() < 0.015:
            inventory_level = None
        if rng.random() < 0.01:
            distance_km = -distance_km  # invalid negative value to be cleaned

        rows.append({
            "OrderID": order_id,
            "OrderDate": order_date.strftime("%Y-%m-%d"),
            "DeliveryDate": delivery_date.strftime("%Y-%m-%d"),
            "SupplierID": supplier,
            "SupplierRegion": supplier_region[supplier],
            "WarehouseID": warehouse,
            "WarehouseRegion": warehouse_region[warehouse],
            "WarehouseCapacity": warehouse_capacity[warehouse],
            "ProductCategory": category,
            "ShelfLifeDays": shelf_life_map[category],
            "TransportMode": mode,
            "DistanceKM": round(distance_km, 2),
            "PlannedLeadTimeDays": round(planned_lead_time, 2),
            "ActualLeadTimeDays": round(actual_lead_time, 2),
            "OrderQuantity": order_quantity,
            "UnitCost": None if pd.isna(unit_cost) else round(unit_cost, 2),
            "ShippingCost": shipping_cost,
            "InventoryLevel": inventory_level,
            "ReorderPoint": reorder_point,
            "CustomerPriority": customer_priority,
            "IsDelayed": is_delayed,
        })

    df = pd.DataFrame(rows)

    # inject a small number of exact duplicate rows (realistic ingestion artifact)
    dup_count = max(1, int(0.005 * len(df)))
    dup_rows = df.sample(n=dup_count, random_state=seed)
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=15000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="../../data/FMCG_data.csv")
    args = parser.parse_args()

    df = generate(args.rows, args.seed)
    df.to_csv(args.out, index=False)
    print(f"Generated {len(df)} rows -> {args.out}")
    print(df.head())
