"""
visualize_optimization.py
==========================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Generates the required optimization visualizations from
``reports/optimization_summary.csv`` and the Week-2 reference tables.

Charts produced (all saved to reports/)
----------------------------------------
    cost_breakdown_chart.png
    decision_comparison_chart.png
    constraint_utilization_chart.png
    supplier_capacity_chart.png
    transportation_cost_heatmap.png
    inventory_usage_chart.png
    optimization_flow_diagram.png

Usage
-----
    python scripts/visualize_optimization.py

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("visualize_optimization")

DATASET_DIR = "dataset"
REPORTS_DIR = "reports"
SUMMARY_PATH = os.path.join(REPORTS_DIR, "optimization_summary.csv")


def _require_summary() -> pd.DataFrame:
    if not os.path.exists(SUMMARY_PATH):
        raise FileNotFoundError(
            f"'{SUMMARY_PATH}' not found. Run scripts/simulate_decisions.py first."
        )
    return pd.read_csv(SUMMARY_PATH)


def plot_cost_breakdown(summary: pd.DataFrame) -> None:
    """Total estimated cost broken down by recommended action."""
    breakdown = summary.groupby("Recommended_Action")["Estimated_Cost_USD"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = sns.color_palette("viridis", len(breakdown))
    ax.bar(breakdown.index, breakdown.values, color=colors)
    ax.set_ylabel("Total Estimated Cost (USD)")
    ax.set_title("Cost Breakdown by Recommended Action")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "cost_breakdown_chart.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved cost breakdown chart.")


def plot_decision_comparison(summary: pd.DataFrame) -> None:
    """Count of shipments per recommended action, colored by tier."""
    pivot = summary.groupby(["Recommended_Action", "Tier"]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 6))
    pivot.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_ylabel("Number of Shipments")
    ax.set_title("Decision Comparison: Recommended Action by Risk Tier")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(title="Tier", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "decision_comparison_chart.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved decision comparison chart.")


def plot_constraint_utilization(summary: pd.DataFrame) -> None:
    """Budget and carbon-budget utilization from the simulation KPIs."""
    import json
    kpi_path = os.path.join(REPORTS_DIR, "optimization_summary.json")
    if not os.path.exists(kpi_path):
        logger.warning("KPI file not found; skipping constraint utilization chart.")
        return
    with open(kpi_path) as f:
        kpis = json.load(f)

    budget_used = kpis.get("total_estimated_cost_usd", 0)
    budget_limit = kpis.get("budget_usd", 1)
    labels = ["Budget"]
    used = [min(budget_used / max(budget_limit, 1), 1.0) * 100]

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, used, color="#ff7f0e", width=0.4)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Utilization (%)")
    ax.axhline(100, color="red", linestyle="--", linewidth=1, label="Capacity Limit")
    for bar, val in zip(bars, used):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 2, f"{val:.1f}%", ha="center")
    ax.set_title("Constraint Utilization: Optimization Budget")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "constraint_utilization_chart.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved constraint utilization chart.")


def plot_supplier_capacity() -> None:
    """Supplier available vs. utilized capacity."""
    path = os.path.join(DATASET_DIR, "supplier_capacity.csv")
    if not os.path.exists(path):
        logger.warning("supplier_capacity.csv not found; skipping chart.")
        return
    df = pd.read_csv(path)
    agg = df.groupby("Supplier_ID")[["Current_Utilization_Units", "Available_Capacity_Units"]].sum()
    agg = agg.sort_values("Current_Utilization_Units", ascending=False).head(20)

    fig, ax = plt.subplots(figsize=(10, 7))
    agg.plot(kind="barh", stacked=True, ax=ax, color=["#d62728", "#2ca02c"])
    ax.set_xlabel("Units")
    ax.set_title("Supplier Capacity: Utilized vs. Available (Top 20 Suppliers)")
    ax.legend(["Utilized", "Available"])
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "supplier_capacity_chart.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved supplier capacity chart.")


def plot_transportation_cost_heatmap() -> None:
    """Cost-per-kg heatmap across transportation modes and lanes (by destination)."""
    path = os.path.join(DATASET_DIR, "shipping_options.csv")
    cost_path = os.path.join(DATASET_DIR, "transportation_cost.csv")
    if not (os.path.exists(path) and os.path.exists(cost_path)):
        logger.warning("shipping_options.csv or transportation_cost.csv not found; skipping heatmap.")
        return
    lanes = pd.read_csv(path)
    rates = pd.read_csv(cost_path).set_index("Mode")["Cost_Per_Kg_USD"]

    lanes["Cost_Per_Kg"] = lanes["Mode"].map(rates)
    pivot = lanes.pivot_table(
        index="Destination_Country", columns="Mode", values="Cost_Per_Kg", aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(8, 8))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax, cbar_kws={"label": "Cost per Kg (USD)"})
    ax.set_title("Transportation Cost Heatmap (USD/kg) by Destination & Mode")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "transportation_cost_heatmap.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved transportation cost heatmap.")


def plot_inventory_usage() -> None:
    """Warehouse inventory: on-hand vs safety-stock, by product category."""
    path = os.path.join(DATASET_DIR, "inventory.csv")
    if not os.path.exists(path):
        logger.warning("inventory.csv not found; skipping chart.")
        return
    df = pd.read_csv(path)
    agg = df.groupby("Product_Category")[["Available_Units", "Safety_Stock_Units"]].sum().sort_values(
        "Available_Units", ascending=False
    )

    fig, ax = plt.subplots(figsize=(9, 6))
    x = np.arange(len(agg))
    width = 0.38
    ax.bar(x - width / 2, agg["Available_Units"], width, label="Available Units", color="#1f77b4")
    ax.bar(x + width / 2, agg["Safety_Stock_Units"], width, label="Safety Stock Units", color="#ff7f0e")
    ax.set_xticks(x)
    ax.set_xticklabels(agg.index, rotation=35, ha="right")
    ax.set_ylabel("Units")
    ax.set_title("Inventory Usage by Product Category")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "inventory_usage_chart.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved inventory usage chart.")


def plot_optimization_flow_diagram() -> None:
    """Static schematic of the decision-engine flow (prediction -> tiering -> optimization -> decision)."""
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.axis("off")

    stages = [
        ("Shipment\nFeatures", "#9ecae1"),
        ("XGBoost\nP(Delay)", "#6baed6"),
        ("Delay-Duration\nRegressor", "#6baed6"),
        ("Business Rule\nTiering", "#fdae6b"),
        ("Cost Function\nEngine", "#a1d99b"),
        ("PuLP MILP\nOptimizer", "#de2d26"),
        ("Recommended\nAction", "#756bb1"),
    ]

    box_w, box_h, gap = 1.5, 1.0, 0.35
    x = 0.2
    centers = []
    for label, color in stages:
        rect = mpatches.FancyBboxPatch(
            (x, 1.0), box_w, box_h, boxstyle="round,pad=0.05,rounding_size=0.08",
            linewidth=1.5, edgecolor="black", facecolor=color,
        )
        ax.add_patch(rect)
        ax.text(x + box_w / 2, 1.0 + box_h / 2, label, ha="center", va="center", fontsize=9, fontweight="bold")
        centers.append(x + box_w)
        x += box_w + gap

    for i in range(len(stages) - 1):
        ax.annotate(
            "", xy=(centers[i] + gap - 0.05, 1.5), xytext=(centers[i], 1.5),
            arrowprops=dict(arrowstyle="->", lw=1.8, color="black"),
        )

    ax.set_xlim(0, x)
    ax.set_ylim(0, 3)
    ax.set_title("SupplyPrescript Decision-Engine Optimization Flow", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(REPORTS_DIR, "optimization_flow_diagram.png"), dpi=150)
    plt.close(fig)
    logger.info("Saved optimization flow diagram.")


def main() -> None:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    summary = _require_summary()

    plot_cost_breakdown(summary)
    plot_decision_comparison(summary)
    plot_constraint_utilization(summary)
    plot_supplier_capacity()
    plot_transportation_cost_heatmap()
    plot_inventory_usage()
    plot_optimization_flow_diagram()

    logger.info("All Week-2 visualizations generated successfully.")


if __name__ == "__main__":
    main()
