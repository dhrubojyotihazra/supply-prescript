"""
generate_optimization_datasets.py
==================================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Synthetic dataset generator for all Operations-Research optimization inputs.

Produces nine linked reference tables that feed the PuLP MILP decision
engine. A sample of shipments from the Week-1 dataset
(``dataset/supply_chain_mock.csv``) is used as the "active shipment batch"
currently in the optimization horizon, so that supplier, transportation,
inventory, warehouse, production, and customer-order data are all
consistent with real shipment attributes (weight, value, priority, lanes).

Output tables (all under ``dataset/``)
---------------------------------------
    suppliers.csv             - primary/secondary supplier master data
    supplier_capacity.csv     - monthly capacity and current utilization per supplier
    transportation_cost.csv   - base rate card per transport mode
    shipping_options.csv      - lane-level (origin/destination/mode) transit + capacity + emissions
    inventory.csv              - on-hand and safety-stock inventory per warehouse/category
    warehouse.csv              - warehouse capacity and storage cost
    production_schedule.csv    - production lines, expedite capability and cost
    customer_orders.csv        - order/customer priority, SLA, and late-penalty terms
    delay_predictions.csv      - Week-1 XGBoost delay probability + estimated delay days

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
import os
import sys

import joblib
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("generate_optimization_datasets")

RANDOM_SEED = 42
DATASET_DIR = "dataset"
ENGINE_DIR = "engine"
SOURCE_DATASET_PATH = os.path.join(DATASET_DIR, "supply_chain_mock.csv")

N_ACTIVE_SHIPMENTS = 400

TRANSPORT_MODES = ["Air", "Sea", "Rail", "Road"]

WAREHOUSES = [f"WH-{i:03d}" for i in range(1, 21)]

PRODUCT_CATEGORIES = [
    "Electronics", "Apparel", "Automotive_Parts", "Pharmaceuticals",
    "Consumer_Goods", "Industrial_Equipment", "Food_Beverage", "Furniture",
]


class OptimizationDatasetGenerator:
    """Generates all nine linked reference tables used by the MILP decision engine."""

    def __init__(self, random_seed: int = RANDOM_SEED):
        self.rng = np.random.default_rng(random_seed)

    # ------------------------------------------------------------------
    def load_active_shipments(self) -> pd.DataFrame:
        """Sample the active shipment batch from the Week-1 dataset."""
        if not os.path.exists(SOURCE_DATASET_PATH):
            raise FileNotFoundError(
                f"Week-1 dataset not found at '{SOURCE_DATASET_PATH}'. "
                "Run Week-1 scripts/generate_dataset.py first."
            )
        df = pd.read_csv(SOURCE_DATASET_PATH, parse_dates=["Order_Date"])
        df = df.drop_duplicates(subset="Shipment_ID").reset_index(drop=True)
        sample = df.sample(n=min(N_ACTIVE_SHIPMENTS, len(df)), random_state=RANDOM_SEED).reset_index(drop=True)
        sample["Product_Category"] = self.rng.choice(PRODUCT_CATEGORIES, size=len(sample))
        sample["Units"] = np.clip((sample["Shipment_Weight"] / self.rng.uniform(0.5, 5.0, len(sample))), 1, None).round(0).astype(int)
        logger.info("Loaded %d active shipments as the optimization horizon batch.", len(sample))
        return sample

    # ------------------------------------------------------------------
    def build_suppliers(self, shipments: pd.DataFrame) -> pd.DataFrame:
        """Primary + secondary supplier master data."""
        primary_ids = sorted(shipments["Supplier_ID"].unique())
        rows = []
        for sid in primary_ids:
            secondary_id = 90000 + sid  # deterministic paired secondary supplier ID
            country = shipments.loc[shipments["Supplier_ID"] == sid, "Supplier_Country"].iloc[0]
            rows.append({
                "Supplier_ID": sid,
                "Supplier_Name": f"Supplier-{sid}",
                "Country": country,
                "Supplier_Type": "Primary",
                "Rating": round(float(np.clip(self.rng.normal(3.8, 0.6), 1, 5)), 2),
                "OnTime_Rate": round(float(np.clip(self.rng.normal(0.86, 0.1), 0.4, 1.0)), 3),
                "Secondary_Supplier_ID": secondary_id,
                "Secondary_Premium_Pct": round(float(self.rng.uniform(0.05, 0.18)), 3),
                "Lead_Time_Days": int(np.clip(self.rng.normal(12, 4), 2, 40)),
            })
            rows.append({
                "Supplier_ID": secondary_id,
                "Supplier_Name": f"Backup-Supplier-{secondary_id}",
                "Country": country,
                "Supplier_Type": "Secondary",
                "Rating": round(float(np.clip(self.rng.normal(3.5, 0.7), 1, 5)), 2),
                "OnTime_Rate": round(float(np.clip(self.rng.normal(0.80, 0.12), 0.4, 1.0)), 3),
                "Secondary_Supplier_ID": np.nan,
                "Secondary_Premium_Pct": np.nan,
                "Lead_Time_Days": int(np.clip(self.rng.normal(8, 3), 2, 30)),
            })
        df = pd.DataFrame(rows)
        logger.info("Generated suppliers.csv with %d supplier records.", len(df))
        return df

    def build_supplier_capacity(self, suppliers: pd.DataFrame) -> pd.DataFrame:
        """Monthly capacity and current utilization per supplier x product category."""
        rows = []
        for _, sup in suppliers.iterrows():
            for category in self.rng.choice(PRODUCT_CATEGORIES, size=3, replace=False):
                max_capacity = int(self.rng.integers(2000, 20000))
                utilization = int(max_capacity * self.rng.uniform(0.4, 0.85))
                rows.append({
                    "Supplier_ID": sup["Supplier_ID"],
                    "Product_Category": category,
                    "Max_Monthly_Capacity_Units": max_capacity,
                    "Current_Utilization_Units": utilization,
                    "Available_Capacity_Units": max_capacity - utilization,
                })
        df = pd.DataFrame(rows)
        logger.info("Generated supplier_capacity.csv with %d records.", len(df))
        return df

    def build_transportation_cost(self) -> pd.DataFrame:
        """Base rate card per transportation mode (mode-level, lane-independent)."""
        base_rates = {
            "Air": {"cost_per_kg": 6.20, "base_fee": 180.0, "co2_per_kg": 1.05, "speed_days_per_1000km": 0.45},
            "Sea": {"cost_per_kg": 0.55, "base_fee": 320.0, "co2_per_kg": 0.015, "speed_days_per_1000km": 3.10},
            "Rail": {"cost_per_kg": 1.10, "base_fee": 150.0, "co2_per_kg": 0.03, "speed_days_per_1000km": 1.40},
            "Road": {"cost_per_kg": 1.85, "base_fee": 90.0, "co2_per_kg": 0.12, "speed_days_per_1000km": 1.05},
        }
        rows = []
        for mode, params in base_rates.items():
            rows.append({
                "Mode": mode,
                "Cost_Per_Kg_USD": params["cost_per_kg"],
                "Base_Fee_USD": params["base_fee"],
                "CO2_Kg_Per_Kg_Shipped": params["co2_per_kg"],
                "Speed_Days_Per_1000Km": params["speed_days_per_1000km"],
            })
        df = pd.DataFrame(rows)
        logger.info("Generated transportation_cost.csv with %d mode rate cards.", len(df))
        return df

    def build_shipping_options(self, shipments: pd.DataFrame, transport_cost: pd.DataFrame) -> pd.DataFrame:
        """Lane-level (origin/destination/mode) transit time, weekly capacity, and availability."""
        lanes = shipments[["Supplier_Country", "Destination_Country"]].drop_duplicates()
        rows = []
        rate_lookup = transport_cost.set_index("Mode").to_dict("index")
        for _, lane in lanes.iterrows():
            origin, destination = lane["Supplier_Country"], lane["Destination_Country"]
            for mode in TRANSPORT_MODES:
                # Sea/Rail unavailable for some intercontinental or short lanes; keep it realistic.
                availability = True
                if mode == "Rail" and origin == destination:
                    availability = self.rng.random() > 0.3
                base_distance_1000km = float(np.clip(self.rng.normal(6.0, 3.0), 0.3, 20.0))
                transit_days = round(rate_lookup[mode]["Speed_Days_Per_1000Km"] * base_distance_1000km, 1)
                weekly_capacity_kg = int(self.rng.integers(5000, 60000)) if mode != "Air" else int(self.rng.integers(2000, 15000))
                rows.append({
                    "Origin_Country": origin,
                    "Destination_Country": destination,
                    "Mode": mode,
                    "Transit_Days": max(transit_days, 0.5),
                    "Weekly_Capacity_Kg": weekly_capacity_kg,
                    "Available": availability,
                })
        df = pd.DataFrame(rows)
        logger.info("Generated shipping_options.csv with %d lane/mode combinations.", len(df))
        return df

    def build_inventory(self) -> pd.DataFrame:
        """On-hand and safety-stock inventory per warehouse x product category."""
        rows = []
        for wh in WAREHOUSES:
            for category in self.rng.choice(PRODUCT_CATEGORIES, size=4, replace=False):
                available = int(self.rng.integers(200, 8000))
                safety_stock = int(available * self.rng.uniform(0.1, 0.3))
                rows.append({
                    "Warehouse_ID": wh,
                    "Product_Category": category,
                    "Available_Units": available,
                    "Safety_Stock_Units": safety_stock,
                    "Usable_Safety_Stock_Units": int(safety_stock * self.rng.uniform(0.5, 0.9)),
                    "Holding_Cost_Per_Unit_USD": round(float(self.rng.uniform(0.15, 2.50)), 2),
                })
        df = pd.DataFrame(rows)
        logger.info("Generated inventory.csv with %d records.", len(df))
        return df

    def build_warehouse(self) -> pd.DataFrame:
        """Warehouse capacity and storage cost."""
        rows = []
        for wh in WAREHOUSES:
            max_capacity = int(self.rng.integers(20000, 120000))
            utilization = int(max_capacity * self.rng.uniform(0.5, 0.9))
            rows.append({
                "Warehouse_ID": wh,
                "Location": f"Region-{self.rng.integers(1, 9)}",
                "Max_Capacity_Units": max_capacity,
                "Current_Utilization_Units": utilization,
                "Available_Capacity_Units": max_capacity - utilization,
                "Storage_Cost_Per_Unit_Per_Day_USD": round(float(self.rng.uniform(0.02, 0.25)), 3),
            })
        df = pd.DataFrame(rows)
        logger.info("Generated warehouse.csv with %d warehouse records.", len(df))
        return df

    def build_production_schedule(self) -> pd.DataFrame:
        """Production lines with expedite capability and cost."""
        rows = []
        for i, category in enumerate(PRODUCT_CATEGORIES):
            for line in range(1, 3):
                can_expedite = bool(self.rng.random() > 0.25)
                rows.append({
                    "Production_ID": f"PROD-{category[:4].upper()}-{line}",
                    "Product_Category": category,
                    "Daily_Capacity_Units": int(self.rng.integers(200, 3000)),
                    "Can_Expedite": can_expedite,
                    "Expedite_Cost_Per_Unit_USD": round(float(self.rng.uniform(0.8, 6.0)), 2) if can_expedite else np.nan,
                    "Max_Expedite_Days": int(self.rng.integers(1, 6)) if can_expedite else 0,
                })
        df = pd.DataFrame(rows)
        logger.info("Generated production_schedule.csv with %d records.", len(df))
        return df

    def build_customer_orders(self, shipments: pd.DataFrame) -> pd.DataFrame:
        """Order/customer priority, SLA, and late-delivery penalty terms per shipment."""
        priority_sla_days = {"Critical": 3, "High": 5, "Medium": 8, "Low": 14}
        priority_penalty_pct_per_day = {"Critical": 0.030, "High": 0.020, "Medium": 0.012, "Low": 0.006}

        rows = []
        for _, s in shipments.iterrows():
            priority = s["Order_Priority"]
            rows.append({
                "Order_ID": f"ORD-{s['Shipment_ID'][-6:]}",
                "Shipment_ID": s["Shipment_ID"],
                "Customer_Type": s["Customer_Type"],
                "Priority": priority,
                "SLA_Max_Delay_Days": priority_sla_days[priority],
                "Order_Value_USD": float(s["Purchase_Order_Value"]),
                "Late_Penalty_Pct_Per_Day": priority_sla_days.get(priority) and priority_penalty_pct_per_day[priority],
                "Units": int(s["Units"]),
            })
        df = pd.DataFrame(rows)
        logger.info("Generated customer_orders.csv with %d records.", len(df))
        return df

    def build_delay_predictions(self, shipments: pd.DataFrame) -> pd.DataFrame:
        """
        Score the active shipment batch with the Week-1 XGBoost classifier and
        the Week-2 delay-duration regressor to produce the ML inputs consumed
        by the optimization decision engine.
        """
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))
        from predict import ShipmentDelayPredictor  # Week-1 classifier wrapper

        predictor = ShipmentDelayPredictor()
        proba_df = predictor.predict(shipments.copy())

        duration_model_path = os.path.join(ENGINE_DIR, "delay_duration_model.joblib")
        duration_pipeline_path = os.path.join(ENGINE_DIR, "preprocessing_pipeline.pkl")
        expected_days = None
        if os.path.exists(duration_model_path):
            duration_model = joblib.load(duration_model_path)
            pipeline = joblib.load(duration_pipeline_path)
            X = pipeline.transform(shipments.copy())
            X = X[pipeline.artifacts.feature_columns]
            expected_days = np.clip(duration_model.predict(X), 0, None)
        else:
            logger.warning(
                "Delay duration model not found at '%s'; falling back to a heuristic estimate. "
                "Run scripts/train_delay_duration_model.py to train it.", duration_model_path
            )
            expected_days = np.clip(
                shipments["Lead_Time"] - shipments["Expected_Lead_Time"], 0, None
            ).values

        result = pd.DataFrame({
            "Shipment_ID": shipments["Shipment_ID"].values,
            "Delay_Probability": proba_df["Delay_Probability"].values,
            "Predicted_Delay_Flag": proba_df["Delay_Prediction"].values,
            "Expected_Delay_Days": np.round(expected_days, 1),
        })
        logger.info(
            "Generated delay_predictions.csv for %d shipments (mean probability=%.3f).",
            len(result), result["Delay_Probability"].mean(),
        )
        return result

    # ------------------------------------------------------------------
    def generate_all(self) -> dict:
        """Generate and save all nine optimization reference tables."""
        os.makedirs(DATASET_DIR, exist_ok=True)
        shipments = self.load_active_shipments()

        suppliers = self.build_suppliers(shipments)
        supplier_capacity = self.build_supplier_capacity(suppliers)
        transportation_cost = self.build_transportation_cost()
        shipping_options = self.build_shipping_options(shipments, transportation_cost)
        inventory = self.build_inventory()
        warehouse = self.build_warehouse()
        production_schedule = self.build_production_schedule()
        customer_orders = self.build_customer_orders(shipments)
        delay_predictions = self.build_delay_predictions(shipments)

        tables = {
            "active_shipments": shipments,
            "suppliers": suppliers,
            "supplier_capacity": supplier_capacity,
            "transportation_cost": transportation_cost,
            "shipping_options": shipping_options,
            "inventory": inventory,
            "warehouse": warehouse,
            "production_schedule": production_schedule,
            "customer_orders": customer_orders,
            "delay_predictions": delay_predictions,
        }

        for name, df in tables.items():
            if name == "active_shipments":
                continue  # Not part of the required table list; used only in-memory.
            path = os.path.join(DATASET_DIR, f"{name}.csv")
            df.to_csv(path, index=False)
            logger.info("Saved '%s' (%d rows).", path, len(df))

        # Persist the active shipment batch too — needed by run_optimizer.py / simulate_decisions.py.
        shipments.to_csv(os.path.join(DATASET_DIR, "active_shipments.csv"), index=False)
        logger.info("Saved 'dataset/active_shipments.csv' (%d rows).", len(shipments))

        return tables


def main() -> None:
    """Entry point for standalone script execution."""
    generator = OptimizationDatasetGenerator()
    generator.generate_all()


if __name__ == "__main__":
    main()
