"""
part1_data_analysis.py
-----------------------
PART 1 - DATA ANALYSIS

Produces a complete per-column profile of FMCG_data.csv:
  - dtype, missing %, duplicates, unique count, cardinality
  - distribution stats, skewness, outlier counts (IQR method)
  - correlation matrix + heatmap
  - histograms / boxplots for numeric columns
  - business-meaning annotations

Outputs land in reports/eda/ and reports/figures/.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("part1_data_analysis")

DATA_PATH = Path("../../data/FMCG_data.csv")
REPORTS_DIR = Path("../../reports/eda")
FIGURES_DIR = Path("../../reports/figures")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (10, 6)

# Business meaning for every column (Part 1 requirement)
BUSINESS_MEANING = {
    "OrderID": "Unique identifier for a purchase order; no predictive value, used for joins/traceability.",
    "OrderDate": "Date the order was placed; drives seasonality, weekday, holiday features.",
    "DeliveryDate": "Actual date goods arrived; combined with OrderDate defines realized lead time.",
    "SupplierID": "Identifies the vendor fulfilling the order; core driver of reliability/risk.",
    "SupplierRegion": "Geographic region of the supplier; proxy for logistics complexity.",
    "WarehouseID": "Destination warehouse for the order; drives capacity and regional risk.",
    "WarehouseRegion": "Geographic region of the receiving warehouse.",
    "WarehouseCapacity": "Max storage capacity (units) of the warehouse; used for inventory coverage ratios.",
    "ProductCategory": "FMCG product line; different categories have different shelf life & demand volatility.",
    "ShelfLifeDays": "Typical shelf life of the product category in days; affects urgency of delivery.",
    "TransportMode": "Mode of shipment (Road/Rail/Air/Sea); major driver of cost and lead time.",
    "DistanceKM": "Distance between supplier and warehouse; drives lead time and shipping cost.",
    "PlannedLeadTimeDays": "Expected/contracted delivery time based on mode + distance.",
    "ActualLeadTimeDays": "Realized delivery time; compared to planned to derive delay.",
    "OrderQuantity": "Units ordered; relates to demand and inventory planning.",
    "UnitCost": "Cost per unit from supplier; feeds total cost calculations.",
    "ShippingCost": "Total freight cost for the shipment.",
    "InventoryLevel": "Current stock at the destination warehouse at order time.",
    "ReorderPoint": "Inventory threshold at which replenishment should trigger.",
    "CustomerPriority": "Business priority tier of the customer/order (Standard/High/Critical).",
    "IsDelayed": "TARGET VARIABLE - 1 if shipment arrived later than planned lead time + 1 day buffer, else 0.",
}


def iqr_outlier_count(series: pd.Series) -> int:
    s = series.dropna()
    if s.empty:
        return 0
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((s < lower) | (s > upper)).sum())


def profile_dataset(df: pd.DataFrame) -> dict:
    profile = {}
    n = len(df)
    for col in df.columns:
        s = df[col]
        entry = {
            "dtype": str(s.dtype),
            "missing_count": int(s.isna().sum()),
            "missing_pct": round(100 * s.isna().sum() / n, 3),
            "unique_count": int(s.nunique(dropna=True)),
            "cardinality_ratio": round(s.nunique(dropna=True) / n, 4),
            "business_meaning": BUSINESS_MEANING.get(col, "N/A"),
        }
        if pd.api.types.is_numeric_dtype(s):
            clean = s.dropna()
            entry.update({
                "mean": float(clean.mean()) if len(clean) else None,
                "median": float(clean.median()) if len(clean) else None,
                "std": float(clean.std()) if len(clean) else None,
                "min": float(clean.min()) if len(clean) else None,
                "max": float(clean.max()) if len(clean) else None,
                "skewness": float(clean.skew()) if len(clean) else None,
                "outlier_count_iqr": iqr_outlier_count(s),
                "negative_value_count": int((clean < 0).sum()),
            })
        else:
            entry.update({
                "top_categories": s.value_counts(dropna=True).head(5).to_dict(),
            })
        profile[col] = entry
    return profile


def main():
    log.info("Loading dataset from %s", DATA_PATH)
    df = pd.read_csv(DATA_PATH)
    log.info("Loaded shape=%s", df.shape)

    duplicate_rows = int(df.duplicated().sum())
    log.info("Duplicate rows: %d", duplicate_rows)

    profile = profile_dataset(df)
    with open(REPORTS_DIR / "column_profile.json", "w") as f:
        json.dump(profile, f, indent=2, default=str)
    log.info("Wrote column_profile.json")

    summary = {
        "n_rows": len(df),
        "n_columns": df.shape[1],
        "duplicate_rows": duplicate_rows,
        "total_missing_cells": int(df.isna().sum().sum()),
        "columns_with_missing": df.columns[df.isna().any()].tolist(),
        "numeric_columns": df.select_dtypes(include=np.number).columns.tolist(),
        "categorical_columns": df.select_dtypes(include="object").columns.tolist(),
    }
    with open(REPORTS_DIR / "dataset_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    log.info("Wrote dataset_summary.json: %s", summary)

    numeric_df = df.select_dtypes(include=np.number)

    # Correlation heatmap
    corr = numeric_df.corr()
    corr.to_csv(REPORTS_DIR / "correlation_matrix.csv")
    plt.figure(figsize=(12, 9))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True)
    plt.title("Correlation Matrix - Numeric Features")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "correlation_heatmap.png", dpi=150)
    plt.close()
    log.info("Saved correlation_heatmap.png")

    # Histograms
    n_cols = len(numeric_df.columns)
    fig, axes = plt.subplots((n_cols + 2) // 3, 3, figsize=(15, 4 * ((n_cols + 2) // 3)))
    axes = axes.flatten()
    for i, col in enumerate(numeric_df.columns):
        sns.histplot(numeric_df[col].dropna(), kde=True, ax=axes[i], color="#4C72B0")
        axes[i].set_title(f"Distribution: {col}")
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "histograms.png", dpi=150)
    plt.close()
    log.info("Saved histograms.png")

    # Boxplots for outlier visualization
    fig, axes = plt.subplots((n_cols + 2) // 3, 3, figsize=(15, 4 * ((n_cols + 2) // 3)))
    axes = axes.flatten()
    for i, col in enumerate(numeric_df.columns):
        sns.boxplot(x=numeric_df[col].dropna(), ax=axes[i], color="#DD8452")
        axes[i].set_title(f"Boxplot: {col}")
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "boxplots.png", dpi=150)
    plt.close()
    log.info("Saved boxplots.png")

    # Target distribution
    plt.figure(figsize=(6, 5))
    sns.countplot(x="IsDelayed", data=df, palette=["#55A868", "#C44E52"])
    plt.title("Shipment Delay Distribution (Target Variable)")
    plt.xlabel("Is Delayed (0=On-time, 1=Delayed)")
    plt.savefig(FIGURES_DIR / "delay_distribution.png", dpi=150)
    plt.close()

    # Delay rate by supplier region / transport mode / category
    for cat_col, fname, title in [
        ("SupplierRegion", "delay_by_supplier_region.png", "Delay Rate by Supplier Region"),
        ("TransportMode", "delay_by_transport_mode.png", "Delay Rate by Transport Mode"),
        ("ProductCategory", "delay_by_product_category.png", "Delay Rate by Product Category"),
    ]:
        rate = df.groupby(cat_col)["IsDelayed"].mean().sort_values(ascending=False)
        plt.figure(figsize=(8, 5))
        sns.barplot(x=rate.values, y=rate.index, color="#4C72B0")
        plt.title(title)
        plt.xlabel("Delay Rate")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / fname, dpi=150)
        plt.close()

    log.info("Part 1 data analysis complete. See reports/eda/ and reports/figures/")


if __name__ == "__main__":
    main()
