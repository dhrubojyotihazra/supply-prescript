"""
run_optimizer.py
=================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
CLI entry point: produce a full recommendation for one shipment.

Usage
-----
    python scripts/run_optimizer.py --shipment-id SHP-100045
    python scripts/run_optimizer.py --random   # pick a random active shipment

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))

from decision_engine import SupplyPrescriptDecisionEngine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("run_optimizer")


def print_recommendation(rec) -> None:
    """Pretty-print a recommendation in the Week-2 spec's example output format."""
    print("\n" + "=" * 60)
    print(f"Shipment ID              : {rec.shipment_id}")
    print(f"Predicted Delay          : {rec.predicted_delay_days:.1f} Days")
    print(f"Delay Probability        : {rec.delay_probability * 100:.1f}%")
    print(f"Tier                     : {rec.tier}")
    print(f"Recommended Action       : {rec.recommended_action}")
    print(f"Estimated Cost           : ${rec.estimated_cost_usd:,.2f}")
    print(f"Expected Delay After Act.: {rec.expected_delay_after_action_days:.1f} Days")
    print(f"Business Impact (Savings): ${rec.business_impact_usd:,.2f}")
    print(f"Optimization Status      : {rec.optimization_status}")
    print(f"Confidence Score         : {rec.confidence_score:.3f}")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SupplyPrescript prescriptive decision engine for one shipment.")
    parser.add_argument("--shipment-id", help="Shipment ID to evaluate (e.g. SHP-100045).")
    parser.add_argument("--random", action="store_true", help="Pick a random active shipment instead.")
    parser.add_argument("--json", action="store_true", help="Print output as JSON instead of formatted text.")
    args = parser.parse_args()

    engine = SupplyPrescriptDecisionEngine()

    if args.random or not args.shipment_id:
        shipment_id = engine.active_shipments.sample(1, random_state=None)["Shipment_ID"].iloc[0]
        logger.info("No --shipment-id given; selected random active shipment: %s", shipment_id)
    else:
        shipment_id = args.shipment_id

    recommendation = engine.recommend_single(shipment_id)

    if args.json:
        print(json.dumps(recommendation.to_dict(), indent=2))
    else:
        print_recommendation(recommendation)


if __name__ == "__main__":
    main()
