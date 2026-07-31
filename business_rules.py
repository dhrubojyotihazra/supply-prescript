"""
business_rules.py
==================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Business-rule tiering: decides HOW MUCH optimization effort a shipment's
predicted delay probability warrants, per the Week-2 specification:

    P(Delay) < 0.40            -> No optimization required.
    0.40 <= P(Delay) < 0.70    -> Recommend one low-cost mitigation strategy
                                   (fast heuristic, not a full MILP).
    P(Delay) >= 0.70           -> Run full joint MILP optimization.

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from cost_function import MitigationOption

logger = logging.getLogger("business_rules")

LOW_RISK_THRESHOLD = 0.40
HIGH_RISK_THRESHOLD = 0.70


class ActionTier(str, Enum):
    """Business-rule tier assigned to a shipment based on delay probability."""

    NO_ACTION = "NO_ACTION_REQUIRED"
    LOW_COST_MITIGATION = "LOW_COST_MITIGATION"
    FULL_OPTIMIZATION = "FULL_OPTIMIZATION"


@dataclass
class TierDecision:
    """The tiering outcome for one shipment."""

    shipment_id: str
    delay_probability: float
    tier: ActionTier
    confidence_score: float


def classify_tier(shipment_id: str, delay_probability: float) -> TierDecision:
    """Classify a shipment into an action tier based on its delay probability."""
    if delay_probability < LOW_RISK_THRESHOLD:
        tier = ActionTier.NO_ACTION
    elif delay_probability < HIGH_RISK_THRESHOLD:
        tier = ActionTier.LOW_COST_MITIGATION
    else:
        tier = ActionTier.FULL_OPTIMIZATION

    # Confidence score: distance of the probability from the nearest decision
    # boundary, normalized to [0, 1] — higher means the tier assignment is
    # less sensitive to small changes in the predicted probability.
    boundaries = [0.0, LOW_RISK_THRESHOLD, HIGH_RISK_THRESHOLD, 1.0]
    nearest_gap = min(abs(delay_probability - b) for b in boundaries if b != delay_probability)
    confidence = round(min(1.0, nearest_gap / 0.20), 3)

    logger.info(
        "Shipment %s: P(Delay)=%.3f -> tier=%s (confidence=%.3f)",
        shipment_id, delay_probability, tier.value, confidence,
    )
    return TierDecision(
        shipment_id=shipment_id,
        delay_probability=delay_probability,
        tier=tier,
        confidence_score=confidence,
    )


def select_low_cost_mitigation(options: list[MitigationOption]) -> Optional[MitigationOption]:
    """
    Fast heuristic for the LOW_COST_MITIGATION tier: pick the cheapest
    feasible option that still brings the shipment within a lenient
    residual-delay bound, without invoking the full MILP solver.

    This trades optimality for speed — appropriate for the 0.40-0.70
    probability band where the business risk does not yet justify the
    computational cost of a full joint optimization across shared resources.
    """
    feasible = [o for o in options if o.feasible and o.cost_usd != float("inf")]
    if not feasible:
        return None

    lenient_bound = 6.0  # days
    within_bound = [o for o in feasible if o.expected_delay_days <= lenient_bound]
    candidates = within_bound if within_bound else feasible

    best = min(candidates, key=lambda o: o.cost_usd)
    logger.info(
        "Low-cost mitigation heuristic selected '%s' for shipment %s (cost=$%.2f, delay=%.1fd).",
        best.option_name, best.shipment_id, best.cost_usd, best.expected_delay_days,
    )
    return best
