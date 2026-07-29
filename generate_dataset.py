"""
generate_dataset.py
====================

SupplyPrescript - Week 1 Predictive Analytics Engine
Synthetic Supply Chain Dataset Generator.

This module produces a realistic, statistically-coherent mock supply chain
dataset used to train the shipment-delay prediction model. Delay risk is
constructed as a function of the generated features (weather severity, port
congestion, supplier reliability, lead time deviation, etc.) rather than
being assigned at random, so that a learning algorithm can extract genuine
signal from the data.

Usage
-----
    python scripts/generate_dataset.py

Output
------
    dataset/supply_chain_mock.csv

Author: SupplyPrescript ML Engineering Team
"""

import logging
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("generate_dataset")

RANDOM_SEED = 42


@dataclass(frozen=True)
class DatasetConfig:
    """Configuration parameters for synthetic dataset generation."""

    n_rows: int = 20_000
    output_path: str = os.path.join("dataset", "supply_chain_mock.csv")
    random_seed: int = RANDOM_SEED


class SupplyChainDatasetGenerator:
    """
    Generates a synthetic, business-realistic supply chain dataset with an
    engineered binary delay target.

    The class encapsulates the full generation workflow: categorical
    reference tables, feature sampling, dependent-feature construction, and
    a logistic delay-risk model used to sample the binary target so that
    the resulting relationships are learnable rather than random noise.
    """

    SUPPLIER_COUNTRIES = [
        "China", "India", "USA", "Germany", "Vietnam",
        "Mexico", "Brazil", "South Korea", "Japan", "Bangladesh",
    ]
    DESTINATION_COUNTRIES = [
        "USA", "Germany", "UK", "France", "Canada",
        "Australia", "Japan", "India", "UAE", "Netherlands",
    ]
    SHIPPING_MODES = ["Air", "Sea", "Rail", "Road"]
    CARRIERS = [
        "Maersk", "DHL", "FedEx", "UPS", "CMA CGM",
        "Kuehne+Nagel", "DB Schenker", "Expeditors",
    ]
    WAREHOUSES = [f"WH-{i:03d}" for i in range(1, 21)]
    ORDER_PRIORITIES = ["Low", "Medium", "High", "Critical"]
    CUSTOMER_TYPES = ["Retail", "Wholesale", "Enterprise", "Government"]
    PACKAGING_TYPES = ["Pallet", "Crate", "Carton", "Drum", "Bulk"]
    PRODUCTION_STATUSES = ["On Schedule", "Delayed", "Ahead of Schedule"]
    CONTAINER_TYPES = ["20ft Dry", "40ft Dry", "Reefer", "Open Top", "Flat Rack"]

    # Shipping mode -> (mean lead time in days, std dev)
    MODE_LEAD_TIME = {
        "Air": (4, 1.5),
        "Road": (7, 2.0),
        "Rail": (10, 2.5),
        "Sea": (25, 5.0),
    }

    def __init__(self, config: DatasetConfig):
        self.config = config
        self.rng = np.random.default_rng(config.random_seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate(self) -> pd.DataFrame:
        """Generate the full synthetic dataset and return it as a DataFrame."""
        logger.info("Generating %d rows of synthetic supply chain data.", self.config.n_rows)

        df = self._generate_base_features()
        df = self._generate_dependent_features(df)
        df = self._generate_target(df)
        df = self._inject_data_quality_issues(df)

        logger.info("Dataset generation complete. Shape: %s", df.shape)
        return df

    def save(self, df: pd.DataFrame) -> None:
        """Persist the generated dataset to disk as CSV."""
        os.makedirs(os.path.dirname(self.config.output_path), exist_ok=True)
        df.to_csv(self.config.output_path, index=False)
        logger.info("Dataset saved to '%s'.", self.config.output_path)

    # ------------------------------------------------------------------
    # Internal generation steps
    # ------------------------------------------------------------------
    def _generate_base_features(self) -> pd.DataFrame:
        """Sample independent business and operational features."""
        n = self.config.n_rows
        rng = self.rng

        shipping_mode = rng.choice(self.SHIPPING_MODES, size=n, p=[0.15, 0.35, 0.20, 0.30])

        dates = pd.date_range("2021-01-01", "2024-12-31", freq="D")
        sampled_dates = rng.choice(dates, size=n)
        sampled_dates = pd.to_datetime(sampled_dates)

        data = {
            "Shipment_ID": [f"SHP-{100000 + i}" for i in range(n)],
            "Supplier_ID": rng.integers(1000, 1500, size=n),
            "Supplier_Rating": np.clip(rng.normal(3.7, 0.7, n), 1.0, 5.0).round(2),
            "Supplier_Country": rng.choice(self.SUPPLIER_COUNTRIES, size=n),
            "Destination_Country": rng.choice(self.DESTINATION_COUNTRIES, size=n),
            "Shipping_Mode": shipping_mode,
            "Carrier": rng.choice(self.CARRIERS, size=n),
            "Warehouse": rng.choice(self.WAREHOUSES, size=n),
            "Historical_Delay_Count": rng.poisson(1.8, n),
            "Inventory_Level": rng.integers(50, 5000, size=n),
            "Demand_Forecast": rng.integers(50, 6000, size=n),
            "Weather_Severity": np.clip(rng.gamma(2.0, 1.2, n), 0, 10).round(2),
            "Holiday_Impact": rng.choice([0, 1], size=n, p=[0.85, 0.15]),
            "Traffic_Index": np.clip(rng.normal(5, 2, n), 0, 10).round(2),
            "Fuel_Price": np.clip(rng.normal(3.4, 0.6, n), 1.5, 6.0).round(2),
            "Port_Congestion": np.clip(rng.gamma(2.2, 1.5, n), 0, 10).round(2),
            "Distance": np.clip(rng.normal(3500, 2000, n), 50, 15000).round(1),
            "Purchase_Order_Value": np.clip(rng.lognormal(9.2, 0.9, n), 100, 500000).round(2),
            "Order_Priority": rng.choice(self.ORDER_PRIORITIES, size=n, p=[0.25, 0.4, 0.25, 0.10]),
            "Customer_Type": rng.choice(self.CUSTOMER_TYPES, size=n),
            "Packaging_Type": rng.choice(self.PACKAGING_TYPES, size=n),
            "Vehicle_Availability": np.clip(rng.normal(75, 15, n), 0, 100).round(1),
            "Production_Status": rng.choice(self.PRODUCTION_STATUSES, size=n, p=[0.65, 0.25, 0.10]),
            "Quality_Score": np.clip(rng.normal(88, 8, n), 40, 100).round(1),
            "Inspection_Delay": np.clip(rng.exponential(1.2, n), 0, 15).round(2),
            "Customs_Clearance_Time": np.clip(rng.exponential(2.0, n), 0, 20).round(2),
            "Container_Type": rng.choice(self.CONTAINER_TYPES, size=n),
            "Shipment_Weight": np.clip(rng.lognormal(6.5, 1.1, n), 5, 40000).round(2),
            "Shipment_Volume": np.clip(rng.lognormal(2.0, 1.0, n), 0.1, 500).round(2),
            "Temperature_Sensitive": rng.choice([0, 1], size=n, p=[0.8, 0.2]),
            "Fragile": rng.choice([0, 1], size=n, p=[0.75, 0.25]),
            "Route_Risk": np.clip(rng.gamma(2.0, 1.3, n), 0, 10).round(2),
            "Carbon_Emission": np.clip(rng.normal(500, 200, n), 10, 3000).round(2),
            "Supplier_OnTime_Rate": np.clip(rng.normal(0.85, 0.12, n), 0.3, 1.0).round(3),
            "Market_Demand_Index": np.clip(rng.normal(50, 15, n), 0, 100).round(1),
            "Geopolitical_Risk": np.clip(rng.gamma(1.8, 1.4, n), 0, 10).round(2),
            "Economic_Index": np.clip(rng.normal(100, 12, n), 50, 150).round(1),
            "Order_Date": sampled_dates,
        }
        return pd.DataFrame(data)

    def _generate_dependent_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Construct features that logically depend on other columns."""
        rng = self.rng
        n = len(df)

        # Expected lead time depends on shipping mode.
        mean_std = df["Shipping_Mode"].map(self.MODE_LEAD_TIME)
        expected_lead_time = np.array([rng.normal(m, s) for m, s in mean_std])
        df["Expected_Lead_Time"] = np.clip(expected_lead_time, 1, 60).round(1)

        # Actual lead time is expected lead time plus risk-driven deviation.
        risk_pressure = (
            0.35 * df["Weather_Severity"]
            + 0.30 * df["Port_Congestion"]
            + 0.25 * df["Route_Risk"]
            + 0.20 * df["Geopolitical_Risk"]
            + 0.15 * df["Customs_Clearance_Time"]
            + 0.10 * df["Inspection_Delay"]
            - 0.20 * (df["Supplier_OnTime_Rate"] * 10)
        )
        noise = rng.normal(0, 0.20, n)
        df["Lead_Time"] = np.clip(
            df["Expected_Lead_Time"] + 3.4 * risk_pressure + noise, 1, 90
        ).round(1)

        # Inventory days derived from inventory level and demand forecast.
        df["Inventory_Days"] = np.clip(
            (df["Inventory_Level"] / (df["Demand_Forecast"] / 30.0 + 1e-3)), 0, 365
        ).round(1)

        # Transportation cost depends on distance, weight, fuel price, mode.
        mode_cost_factor = df["Shipping_Mode"].map({"Air": 4.5, "Road": 1.2, "Rail": 0.9, "Sea": 0.5})
        df["Transportation_Cost"] = (
            (df["Distance"] * 0.05 + df["Shipment_Weight"] * 0.02)
            * mode_cost_factor
            * (df["Fuel_Price"] / 3.4)
        ).round(2)

        # Late delivery cost as a business penalty proxy.
        df["Late_Delivery_Cost"] = (
            df["Purchase_Order_Value"] * 0.02
            + df["Transportation_Cost"] * 0.10
        ).round(2)

        # Supplier risk category derived from rating and on-time rate.
        supplier_score = df["Supplier_Rating"] / 5.0 * 0.5 + df["Supplier_OnTime_Rate"] * 0.5
        df["Supplier_Risk"] = pd.cut(
            supplier_score, bins=[0, 0.55, 0.75, 1.0], labels=["High", "Medium", "Low"]
        ).astype(str)

        # Calendar-derived features.
        df["Month"] = df["Order_Date"].dt.month
        df["Quarter"] = df["Order_Date"].dt.quarter
        df["Week"] = df["Order_Date"].dt.isocalendar().week.astype(int)
        df["Year"] = df["Order_Date"].dt.year

        return df

    def _generate_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Construct the binary Delay target using a logistic risk function of
        the engineered features so that predictive signal exists.
        """
        rng = self.rng

        # Normalize key drivers to comparable ranges before combining.
        lead_time_gap = (df["Lead_Time"] - df["Expected_Lead_Time"]) / (df["Expected_Lead_Time"] + 1e-3)

        z = (
            -5.55
            + 11.50 * lead_time_gap
            + 0.80 * (df["Weather_Severity"] / 10)
            + 1.05 * (df["Port_Congestion"] / 10)
            + 0.75 * (df["Route_Risk"] / 10)
            + 0.70 * (df["Geopolitical_Risk"] / 10)
            + 0.50 * (df["Customs_Clearance_Time"] / 20)
            + 0.45 * (df["Inspection_Delay"] / 15)
            + 0.60 * df["Holiday_Impact"]
            + 0.65 * (df["Historical_Delay_Count"] / (df["Historical_Delay_Count"].max() + 1))
            - 1.30 * df["Supplier_OnTime_Rate"]
            - 0.55 * (df["Supplier_Rating"] / 5)
            + 0.35 * (df["Production_Status"] == "Delayed").astype(int)
            - 0.35 * (df["Vehicle_Availability"] / 100)
            + 0.28 * (df["Order_Priority"] == "Critical").astype(int)
        )

        probability = 1 / (1 + np.exp(-z))
        df["Delay_Probability_Latent"] = probability.round(4)
        df["Delay"] = (rng.random(len(df)) < probability).astype(int)

        # Drop the latent probability column; it is a generation artifact,
        # not a feature that would be available at inference time.
        df = df.drop(columns=["Delay_Probability_Latent"])

        delay_rate = df["Delay"].mean()
        logger.info("Generated target distribution -> Delay rate: %.2f%%", delay_rate * 100)
        return df

    def _inject_data_quality_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Inject realistic data quality issues (missing values, duplicates)
        so the preprocessing pipeline has genuine work to do.
        """
        rng = self.rng
        n = len(df)

        # Inject missing values (~2-4%) into a subset of columns that would
        # plausibly be missing in a real operational data warehouse.
        missingness_columns = [
            "Supplier_Rating", "Weather_Severity", "Quality_Score",
            "Vehicle_Availability", "Customs_Clearance_Time", "Port_Congestion",
        ]
        for col in missingness_columns:
            frac = rng.uniform(0.02, 0.04)
            mask = rng.random(n) < frac
            df.loc[mask, col] = np.nan

        # Inject a small number of exact duplicate rows.
        n_duplicates = max(1, int(n * 0.005))
        duplicate_rows = df.sample(n=n_duplicates, random_state=self.config.random_seed)
        df = pd.concat([df, duplicate_rows], ignore_index=True)

        logger.info(
            "Injected missing values into %d columns and %d duplicate rows.",
            len(missingness_columns), n_duplicates,
        )
        return df


def main() -> None:
    """Entry point for standalone script execution."""
    config = DatasetConfig()
    generator = SupplyChainDatasetGenerator(config)
    df = generator.generate()
    generator.save(df)


if __name__ == "__main__":
    main()
