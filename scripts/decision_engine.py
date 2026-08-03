"""
decision_engine.py
===================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Top-level orchestrator: integrates the Week-1 XGBoost delay classifier and
the Week-2 delay-duration regressor with the business-rule tiering,
cost-function engine, and PuLP joint optimizer to produce the final,
business-readable recommendation for one or many shipments.

This is the intended integration point for the future FastAPI service layer
(``POST /recommend``, ``POST /recommend-batch``).

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import joblib
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from business_rules import ActionTier, TierDecision, classify_tier, select_low_cost_mitigation  # noqa: E402
from constraint_builder import ConstraintBuilder, OptimizationConstraints  # noqa: E402
from cost_function import CostFunctionEngine, MitigationOption  # noqa: E402
from optimizer import BatchOptimizationResult, PrescriptiveOptimizer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("decision_engine")

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(ENGINE_DIR, "..", "dataset")

MODEL_PATH = os.path.join(ENGINE_DIR, "xgboost_model.joblib")
DURATION_MODEL_PATH = os.path.join(ENGINE_DIR, "delay_duration_model.joblib")
PIPELINE_PATH = os.path.join(ENGINE_DIR, "preprocessing_pipeline.pkl")

DEFAULT_BUDGET_USD = 500_000.0
DEFAULT_CARBON_LIMIT_KG = 250_000.0


class DecisionEngineError(Exception):
    """Raised when a fatal error occurs in the decision engine."""


@dataclass
class ShipmentRecommendation:
    """Final, business-readable output for a single shipment."""

    shipment_id: str
    predicted_delay_days: float
    delay_probability: float
    tier: str
    recommended_action: str
    estimated_cost_usd: float
    expected_delay_after_action_days: float
    business_impact_usd: float
    optimization_status: str
    confidence_score: float

    def to_dict(self) -> dict:
        return {
            "Shipment_ID": self.shipment_id,
            "Predicted_Delay_Days": self.predicted_delay_days,
            "Delay_Probability": self.delay_probability,
            "Tier": self.tier,
            "Recommended_Action": self.recommended_action,
            "Estimated_Cost_USD": self.estimated_cost_usd,
            "Expected_Delay_After_Action_Days": self.expected_delay_after_action_days,
            "Business_Impact_USD": self.business_impact_usd,
            "Optimization_Status": self.optimization_status,
            "Confidence_Score": self.confidence_score,
        }


class SupplyPrescriptDecisionEngine:
    """
    End-to-end prescriptive decision engine: ML prediction -> business-rule
    tiering -> cost-function bundling -> (heuristic or full MILP)
    optimization -> business-readable recommendation.
    """

    def __init__(self, dataset_dir: str = DATASET_DIR):
        self.dataset_dir = dataset_dir
        self._load_ml_artifacts()
        self._load_reference_tables()

    # ------------------------------------------------------------------
    def _load_ml_artifacts(self) -> None:
        if not os.path.exists(MODEL_PATH) or not os.path.exists(PIPELINE_PATH):
            raise DecisionEngineError(
                "Week-1 model artifacts not found. Run Week-1 scripts/train_model.py first."
            )
        self.classifier = joblib.load(MODEL_PATH)
        self.pipeline = joblib.load(PIPELINE_PATH)
        self.duration_model = joblib.load(DURATION_MODEL_PATH) if os.path.exists(DURATION_MODEL_PATH) else None
        if self.duration_model is None:
            logger.warning(
                "Delay-duration model not found; expected-delay-days will use a fallback heuristic. "
                "Run scripts/train_delay_duration_model.py to train it."
            )
        logger.info("Loaded ML artifacts (classifier, pipeline, duration model).")

    def _load_reference_tables(self) -> None:
        def _p(name: str) -> str:
            return os.path.join(self.dataset_dir, name)

        required = [
            "suppliers.csv", "supplier_capacity.csv", "transportation_cost.csv",
            "shipping_options.csv", "inventory.csv", "warehouse.csv",
            "production_schedule.csv", "customer_orders.csv", "active_shipments.csv",
        ]
        missing = [f for f in required if not os.path.exists(_p(f))]
        if missing:
            raise DecisionEngineError(
                f"Missing Week-2 reference tables: {missing}. "
                "Run scripts/generate_optimization_datasets.py first."
            )

        self.suppliers = pd.read_csv(_p("suppliers.csv"))
        self.supplier_capacity = pd.read_csv(_p("supplier_capacity.csv"))
        self.transportation_cost = pd.read_csv(_p("transportation_cost.csv"))
        self.shipping_options = pd.read_csv(_p("shipping_options.csv"))
        self.inventory = pd.read_csv(_p("inventory.csv"))
        self.warehouse = pd.read_csv(_p("warehouse.csv"))
        self.production_schedule = pd.read_csv(_p("production_schedule.csv"))
        self.customer_orders = pd.read_csv(_p("customer_orders.csv"))
        self.active_shipments = pd.read_csv(_p("active_shipments.csv"), parse_dates=["Order_Date"])

        self.cost_engine = CostFunctionEngine(
            suppliers=self.suppliers,
            supplier_capacity=self.supplier_capacity,
            transportation_cost=self.transportation_cost,
            shipping_options=self.shipping_options,
            inventory=self.inventory,
            warehouse=self.warehouse,
            production_schedule=self.production_schedule,
            customer_orders=self.customer_orders,
        )
        self.constraint_builder = ConstraintBuilder(
            shipping_options=self.shipping_options,
            supplier_capacity=self.supplier_capacity,
            inventory=self.inventory,
            warehouse=self.warehouse,
            production_schedule=self.production_schedule,
            customer_orders=self.customer_orders,
        )
        logger.info("Loaded all Week-2 reference tables (%d active shipments).", len(self.active_shipments))

    # ------------------------------------------------------------------
    def predict_delay(self, shipments: pd.DataFrame) -> pd.DataFrame:
        """Score shipments with the Week-1 classifier + Week-2 duration regressor."""
        X_full = self.pipeline.transform(shipments.copy())
        X = X_full[self.pipeline.artifacts.feature_columns]

        probability = self.classifier.predict_proba(X)[:, 1]
        if self.duration_model is not None:
            expected_days = np.clip(self.duration_model.predict(X), 0, None)
        else:
            expected_days = np.clip(
                shipments["Expected_Lead_Time"].values * 0.15, 0, None
            )  # crude fallback heuristic

        return pd.DataFrame({
            "Shipment_ID": shipments["Shipment_ID"].values,
            "Delay_Probability": np.round(probability, 4),
            "Expected_Delay_Days": np.round(expected_days, 1),
        })

    # ------------------------------------------------------------------
    def recommend_single(self, shipment_id: str) -> ShipmentRecommendation:
        """Produce a full recommendation for a single shipment (real-time path)."""
        row = self.active_shipments[self.active_shipments["Shipment_ID"] == shipment_id]
        if row.empty:
            raise DecisionEngineError(f"Shipment '{shipment_id}' not found in active shipment batch.")
        shipment = row.iloc[0]

        prediction = self.predict_delay(row).iloc[0]
        probability = float(prediction["Delay_Probability"])
        expected_delay_days = float(prediction["Expected_Delay_Days"])

        tier_decision = classify_tier(shipment_id, probability)

        if tier_decision.tier == ActionTier.NO_ACTION:
            return ShipmentRecommendation(
                shipment_id=shipment_id,
                predicted_delay_days=expected_delay_days,
                delay_probability=probability,
                tier=tier_decision.tier.value,
                recommended_action="No_Action_Required",
                estimated_cost_usd=0.0,
                expected_delay_after_action_days=expected_delay_days,
                business_impact_usd=0.0,
                optimization_status="Not_Required",
                confidence_score=tier_decision.confidence_score,
            )

        options = self.cost_engine.build_options(shipment, expected_delay_days)

        if tier_decision.tier == ActionTier.LOW_COST_MITIGATION:
            best = select_low_cost_mitigation(options)
            if best is None:
                return self._no_feasible_option_result(shipment_id, prediction, tier_decision)
            baseline = next((o for o in options if o.option_name == "Delay_Launch"), None)
            savings = round((baseline.cost_usd if baseline else best.cost_usd) - best.cost_usd, 2)
            return ShipmentRecommendation(
                shipment_id=shipment_id,
                predicted_delay_days=expected_delay_days,
                delay_probability=probability,
                tier=tier_decision.tier.value,
                recommended_action=best.option_name,
                estimated_cost_usd=best.cost_usd,
                expected_delay_after_action_days=best.expected_delay_days,
                business_impact_usd=savings,
                optimization_status="Heuristic_Optimal",
                confidence_score=tier_decision.confidence_score,
            )

        # FULL_OPTIMIZATION tier: run the joint MILP for this single shipment,
        # respecting current system-wide resource availability.
        constraints = self.constraint_builder.build(
            shipment_ids=[shipment_id], budget_usd=DEFAULT_BUDGET_USD, carbon_limit_kg=DEFAULT_CARBON_LIMIT_KG,
        )
        optimizer = PrescriptiveOptimizer(
            constraints=constraints,
            order_value_lookup={shipment_id: float(shipment["Purchase_Order_Value"])},
            late_penalty_pct_lookup=self._penalty_pct_lookup([shipment_id]),
            priority_lookup=self._priority_lookup([shipment_id]),
        )
        result = optimizer.solve({shipment_id: options})
        shipment_result = result.shipment_results[shipment_id]
        selected = shipment_result.selected_option

        if selected is None:
            return self._no_feasible_option_result(shipment_id, prediction, tier_decision)

        return ShipmentRecommendation(
            shipment_id=shipment_id,
            predicted_delay_days=expected_delay_days,
            delay_probability=probability,
            tier=tier_decision.tier.value,
            recommended_action=selected.option_name,
            estimated_cost_usd=selected.cost_usd,
            expected_delay_after_action_days=selected.expected_delay_days,
            business_impact_usd=result.total_savings_usd,
            optimization_status=result.status,
            confidence_score=tier_decision.confidence_score,
        )

    def _no_feasible_option_result(self, shipment_id, prediction, tier_decision) -> ShipmentRecommendation:
        logger.warning("No feasible mitigation option found for shipment %s.", shipment_id)
        return ShipmentRecommendation(
            shipment_id=shipment_id,
            predicted_delay_days=float(prediction["Expected_Delay_Days"]),
            delay_probability=float(prediction["Delay_Probability"]),
            tier=tier_decision.tier.value,
            recommended_action="No_Feasible_Option",
            estimated_cost_usd=0.0,
            expected_delay_after_action_days=float(prediction["Expected_Delay_Days"]),
            business_impact_usd=0.0,
            optimization_status="Infeasible",
            confidence_score=tier_decision.confidence_score,
        )

    # ------------------------------------------------------------------
    def recommend_batch(
        self, shipment_ids: list[str], budget_usd: float = DEFAULT_BUDGET_USD,
        carbon_limit_kg: float = DEFAULT_CARBON_LIMIT_KG,
    ) -> tuple[list[ShipmentRecommendation], BatchOptimizationResult]:
        """
        Produce recommendations for a batch of shipments using a SINGLE joint
        MILP for all shipments assigned to the FULL_OPTIMIZATION tier, so
        they properly compete for shared transportation/supplier/inventory/
        production capacity. NO_ACTION and LOW_COST_MITIGATION shipments are
        resolved with the lightweight paths as usual.
        """
        rows = self.active_shipments[self.active_shipments["Shipment_ID"].isin(shipment_ids)].reset_index(drop=True)
        if rows.empty:
            raise DecisionEngineError("None of the requested shipment IDs were found in the active batch.")

        predictions = self.predict_delay(rows).set_index("Shipment_ID")

        recommendations: list[ShipmentRecommendation] = []
        full_opt_options: dict[str, list[MitigationOption]] = {}
        full_opt_shipment_rows: dict[str, pd.Series] = {}

        for _, shipment in rows.iterrows():
            sid = shipment["Shipment_ID"]
            probability = float(predictions.loc[sid, "Delay_Probability"])
            expected_delay_days = float(predictions.loc[sid, "Expected_Delay_Days"])
            tier_decision = classify_tier(sid, probability)

            if tier_decision.tier == ActionTier.NO_ACTION:
                recommendations.append(ShipmentRecommendation(
                    shipment_id=sid, predicted_delay_days=expected_delay_days, delay_probability=probability,
                    tier=tier_decision.tier.value, recommended_action="No_Action_Required",
                    estimated_cost_usd=0.0, expected_delay_after_action_days=expected_delay_days,
                    business_impact_usd=0.0, optimization_status="Not_Required",
                    confidence_score=tier_decision.confidence_score,
                ))
                continue

            options = self.cost_engine.build_options(shipment, expected_delay_days)

            if tier_decision.tier == ActionTier.LOW_COST_MITIGATION:
                best = select_low_cost_mitigation(options)
                if best is None:
                    recommendations.append(self._no_feasible_option_result(sid, predictions.loc[sid], tier_decision))
                    continue
                baseline = next((o for o in options if o.option_name == "Delay_Launch"), None)
                savings = round((baseline.cost_usd if baseline else best.cost_usd) - best.cost_usd, 2)
                recommendations.append(ShipmentRecommendation(
                    shipment_id=sid, predicted_delay_days=expected_delay_days, delay_probability=probability,
                    tier=tier_decision.tier.value, recommended_action=best.option_name,
                    estimated_cost_usd=best.cost_usd, expected_delay_after_action_days=best.expected_delay_days,
                    business_impact_usd=savings, optimization_status="Heuristic_Optimal",
                    confidence_score=tier_decision.confidence_score,
                ))
                continue

            # FULL_OPTIMIZATION tier: defer to the joint batch MILP below.
            full_opt_options[sid] = options
            full_opt_shipment_rows[sid] = shipment

        batch_result = None
        if full_opt_options:
            constraints = self.constraint_builder.build(
                shipment_ids=list(full_opt_options.keys()), budget_usd=budget_usd, carbon_limit_kg=carbon_limit_kg,
            )
            optimizer = PrescriptiveOptimizer(
                constraints=constraints,
                order_value_lookup=self._order_value_lookup(full_opt_shipment_rows),
                late_penalty_pct_lookup=self._penalty_pct_lookup(list(full_opt_options.keys())),
                priority_lookup=self._priority_lookup(list(full_opt_options.keys())),
            )
            batch_result = optimizer.solve(full_opt_options)

            for sid, shipment_result in batch_result.shipment_results.items():
                probability = float(predictions.loc[sid, "Delay_Probability"])
                expected_delay_days = float(predictions.loc[sid, "Expected_Delay_Days"])
                selected = shipment_result.selected_option
                tier_decision = classify_tier(sid, probability)

                if selected is None:
                    recommendations.append(self._no_feasible_option_result(sid, predictions.loc[sid], tier_decision))
                    continue

                recommendations.append(ShipmentRecommendation(
                    shipment_id=sid, predicted_delay_days=expected_delay_days, delay_probability=probability,
                    tier=tier_decision.tier.value, recommended_action=selected.option_name,
                    estimated_cost_usd=selected.cost_usd, expected_delay_after_action_days=selected.expected_delay_days,
                    business_impact_usd=shipment_result.total_cost, optimization_status=batch_result.status,
                    confidence_score=tier_decision.confidence_score,
                ))

        return recommendations, batch_result

    # ------------------------------------------------------------------
    def _order_value_lookup(self, shipment_rows: dict[str, pd.Series]) -> dict:
        return {sid: float(row["Purchase_Order_Value"]) for sid, row in shipment_rows.items()}

    def _penalty_pct_lookup(self, shipment_ids: list[str]) -> dict:
        orders = self.customer_orders.set_index("Shipment_ID")
        lookup = {}
        for sid in shipment_ids:
            if sid in orders.index:
                lookup[sid] = float(orders.loc[sid, "Late_Penalty_Pct_Per_Day"])
        return lookup

    def _priority_lookup(self, shipment_ids: list[str]) -> dict:
        orders = self.customer_orders.set_index("Shipment_ID")
        lookup = {}
        for sid in shipment_ids:
            if sid in orders.index:
                lookup[sid] = str(orders.loc[sid, "Priority"])
        return lookup
