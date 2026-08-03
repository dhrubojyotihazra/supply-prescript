"""
simulate_decisions.py
======================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Scenario simulator: runs the full decision engine (business-rule tiering +
joint MILP optimization for high-risk shipments) across the entire active
shipment batch, and writes a business-ready optimization summary report.

Usage
-----
    python scripts/simulate_decisions.py --budget 500000 --carbon-limit 250000

Output
------
    reports/optimization_summary.csv
    reports/optimization_summary.json  (aggregate KPIs)

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))

from decision_engine import DEFAULT_BUDGET_USD, DEFAULT_CARBON_LIMIT_KG, SupplyPrescriptDecisionEngine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("simulate_decisions")

REPORTS_DIR = "reports"
SUMMARY_CSV_PATH = os.path.join(REPORTS_DIR, "optimization_summary.csv")
SUMMARY_JSON_PATH = os.path.join(REPORTS_DIR, "optimization_summary.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate prescriptive decisions across the active shipment batch.")
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD, help="Total mitigation budget (USD).")
    parser.add_argument("--carbon-limit", type=float, default=DEFAULT_CARBON_LIMIT_KG, help="Total carbon budget (kg CO2).")
    parser.add_argument("--sample-size", type=int, default=None, help="Optionally limit to N active shipments.")
    args = parser.parse_args()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    engine = SupplyPrescriptDecisionEngine()

    shipment_ids = engine.active_shipments["Shipment_ID"].tolist()
    if args.sample_size:
        shipment_ids = shipment_ids[: args.sample_size]

    logger.info("Running scenario simulation for %d shipments (budget=$%.0f, carbon_limit=%.0fkg).",
                len(shipment_ids), args.budget, args.carbon_limit)

    recommendations, batch_result = engine.recommend_batch(
        shipment_ids, budget_usd=args.budget, carbon_limit_kg=args.carbon_limit
    )

    summary_df = pd.DataFrame([r.to_dict() for r in recommendations])
    summary_df.to_csv(SUMMARY_CSV_PATH, index=False)
    logger.info("Saved optimization summary to '%s' (%d rows).", SUMMARY_CSV_PATH, len(summary_df))

    tier_counts = summary_df["Tier"].value_counts().to_dict()
    action_counts = summary_df["Recommended_Action"].value_counts().to_dict()

    kpis = {
        "total_shipments_evaluated": len(summary_df),
        "tier_distribution": tier_counts,
        "recommended_action_distribution": action_counts,
        "total_estimated_cost_usd": round(float(summary_df["Estimated_Cost_USD"].sum()), 2),
        "total_business_impact_usd": round(float(summary_df["Business_Impact_USD"].sum()), 2),
        "average_delay_probability": round(float(summary_df["Delay_Probability"].mean()), 4),
        "average_expected_delay_days_after_action": round(float(summary_df["Expected_Delay_After_Action_Days"].mean()), 2),
        "joint_milp_status": batch_result.status if batch_result else "Not_Invoked",
        "joint_milp_solver_time_seconds": batch_result.solver_time_seconds if batch_result else 0.0,
        "budget_usd": args.budget,
        "carbon_limit_kg": args.carbon_limit,
    }

    with open(SUMMARY_JSON_PATH, "w") as f:
        json.dump(kpis, f, indent=2)
    logger.info("Saved aggregate KPIs to '%s'.", SUMMARY_JSON_PATH)
    logger.info("Simulation KPIs:\n%s", json.dumps(kpis, indent=2))


if __name__ == "__main__":
    main()
