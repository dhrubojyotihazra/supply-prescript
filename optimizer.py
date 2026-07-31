"""
optimizer.py
============

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Mixed-Integer Linear Program (MILP) for joint shipment mitigation decisions.

Given a batch of shipments (each with a set of pre-costed
:class:`~engine.cost_function.MitigationOption` candidates) and a shared
:class:`~engine.constraint_builder.OptimizationConstraints`, this module
builds and solves a PuLP MILP that:

    * chooses exactly one mitigation option per shipment (binary decision
      variables),
    * enforces shared resource-capacity constraints across ALL shipments in
      the batch (transportation, supplier, inventory, production,
      warehouse),
    * enforces a hard SLA (maximum acceptable delay) for high/critical
      priority shipments, and a soft (penalized) SLA for lower-priority
      shipments via an auxiliary "days-over-SLA" continuous variable,
    * enforces a total budget cap and a total carbon-emission cap,
    * minimizes total business cost = sum of bundled option costs + late
      delivery penalty cost + explicit carbon cost.

This is a genuine joint/batch optimization (not per-shipment greedy
selection): shipments compete for the same limited transportation lanes,
supplier capacity, safety stock, and production expediting slots, so the
optimizer must trade off which shipments get the premium mitigation and
which absorb a shorter delay or penalty.

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pulp

from constraint_builder import OptimizationConstraints
from cost_function import CARBON_PRICE_PER_KG_USD, MitigationOption

logger = logging.getLogger("optimizer")

LATE_PENALTY_PCT_PER_DAY_DEFAULT = 0.015  # Fallback late-penalty rate if not supplied per shipment.
BIG_M_DELAY_DAYS = 365


@dataclass
class ShipmentOptimizationResult:
    """Solved outcome for a single shipment within a batch optimization run."""

    shipment_id: str
    selected_option: Optional[MitigationOption]
    all_options: list  # list[MitigationOption] with a `.selected` bool set post-solve
    days_over_sla: float
    late_penalty_cost: float
    carbon_cost: float
    total_cost: float


@dataclass
class BatchOptimizationResult:
    """Full solved outcome for a batch (joint) optimization run."""

    status: str
    total_cost_usd: float
    total_savings_usd: float
    shipment_results: dict  # {shipment_id: ShipmentOptimizationResult}
    solver_time_seconds: float
    constraint_utilization: dict = field(default_factory=dict)


class PrescriptiveOptimizer:
    """
    Builds and solves the joint shipment-mitigation MILP using PuLP with the
    CBC backend solver.
    """

    def __init__(self, constraints: OptimizationConstraints, order_value_lookup: Optional[dict] = None,
                 late_penalty_pct_lookup: Optional[dict] = None, priority_lookup: Optional[dict] = None,
                 hard_sla_priorities: tuple = ("Critical", "High")):
        self.constraints = constraints
        self.order_value_lookup = order_value_lookup or {}
        self.late_penalty_pct_lookup = late_penalty_pct_lookup or {}
        self.priority_lookup = priority_lookup or {}
        self.hard_sla_priorities = hard_sla_priorities

    # ------------------------------------------------------------------
    def solve(self, shipment_options: dict[str, list[MitigationOption]]) -> BatchOptimizationResult:
        """
        Solve the joint MILP.

        Parameters
        ----------
        shipment_options : dict[str, list[MitigationOption]]
            Mapping of shipment_id -> list of candidate MitigationOption
            objects (as produced by CostFunctionEngine.build_options).
        """
        prob = pulp.LpProblem("SupplyPrescript_Joint_Mitigation", pulp.LpMinimize)

        # ---------------- Decision variables ----------------
        x = {}  # x[(shipment_id, option_name)] = binary variable
        for sid, options in shipment_options.items():
            for opt in options:
                if not opt.feasible or opt.cost_usd == float("inf"):
                    continue
                x[(sid, opt.option_name)] = pulp.LpVariable(
                    f"x_{sid}_{opt.option_name}", cat="Binary"
                )

        # Auxiliary continuous variables: days over SLA per shipment (soft-SLA shipments only).
        over_sla = {
            sid: pulp.LpVariable(f"over_sla_{sid}", lowBound=0, cat="Continuous")
            for sid in shipment_options
        }

        # ---------------- Objective function ----------------
        cost_terms = []
        for sid, options in shipment_options.items():
            for opt in options:
                key = (sid, opt.option_name)
                if key not in x:
                    continue
                carbon_cost = opt.emission_kg * CARBON_PRICE_PER_KG_USD
                cost_terms.append((opt.cost_usd + carbon_cost) * x[key])

            penalty_pct = self.late_penalty_pct_lookup.get(sid, LATE_PENALTY_PCT_PER_DAY_DEFAULT)
            order_value = self.order_value_lookup.get(sid, 0.0)
            cost_terms.append(order_value * penalty_pct * over_sla[sid])

        prob += pulp.lpSum(cost_terms), "Total_Business_Cost"

        # ---------------- Constraint: exactly one option per shipment ----------------
        for sid, options in shipment_options.items():
            available_keys = [(sid, opt.option_name) for opt in options if (sid, opt.option_name) in x]
            if not available_keys:
                logger.warning("Shipment %s has no feasible mitigation options; skipping selection constraint.", sid)
                continue
            prob += pulp.lpSum(x[k] for k in available_keys) == 1, f"OneOption_{sid}"

        # ---------------- Constraint: SLA / maximum acceptable delay ----------------
        for sid, options in shipment_options.items():
            priority = self.priority_lookup.get(sid, "Medium")
            sla = self.constraints.sla_days.get(sid, 8.0)
            delay_expr = pulp.lpSum(
                opt.expected_delay_days * x[(sid, opt.option_name)]
                for opt in options if (sid, opt.option_name) in x
            )
            if priority in self.hard_sla_priorities:
                prob += delay_expr <= sla, f"HardSLA_{sid}"
                prob += over_sla[sid] == 0, f"NoSoftSLA_{sid}"
            else:
                prob += over_sla[sid] >= delay_expr - sla, f"SoftSLA_{sid}"

        # ---------------- Constraint: budget ----------------
        budget_terms = [
            opt.cost_usd * x[(sid, opt.option_name)]
            for sid, options in shipment_options.items()
            for opt in options if (sid, opt.option_name) in x
        ]
        if budget_terms:
            prob += pulp.lpSum(budget_terms) <= self.constraints.budget_usd, "Total_Budget"

        # ---------------- Constraint: carbon emission limit ----------------
        carbon_terms = [
            opt.emission_kg * x[(sid, opt.option_name)]
            for sid, options in shipment_options.items()
            for opt in options if (sid, opt.option_name) in x
        ]
        if carbon_terms:
            prob += pulp.lpSum(carbon_terms) <= self.constraints.carbon_limit_kg, "Carbon_Limit"

        # ---------------- Constraint: shared resource capacities ----------------
        self._add_resource_constraints(prob, x, shipment_options, "transport_mode",
                                        self.constraints.transport_capacity_kg, "Transport")
        self._add_resource_constraints(prob, x, shipment_options, "supplier",
                                        self.constraints.supplier_capacity_units, "Supplier")
        self._add_resource_constraints(prob, x, shipment_options, "inventory",
                                        self.constraints.inventory_capacity_units, "Inventory")
        self._add_resource_constraints(prob, x, shipment_options, "production",
                                        self.constraints.production_capacity_units, "Production")

        # ---------------- Solve ----------------
        from solver import MilpSolver
        milp_solver = MilpSolver()
        outcome = milp_solver.solve(prob)
        status_str = outcome.status
        elapsed = outcome.elapsed_seconds

        return self._extract_results(prob, x, over_sla, shipment_options, status_str, elapsed)

    # ------------------------------------------------------------------
    def _add_resource_constraints(self, prob, x, shipment_options, resource_type, capacity_map, label):
        """Add shared-resource capacity constraints (sum of usage across all shipments <= capacity)."""
        usage_by_key: dict[str, list] = {}
        for sid, options in shipment_options.items():
            for opt in options:
                key = (sid, opt.option_name)
                if key not in x or opt.resource_type != resource_type or opt.resource_key is None:
                    continue
                usage_by_key.setdefault(opt.resource_key, []).append(
                    opt.resource_units_required * x[key]
                )

        for resource_key, terms in usage_by_key.items():
            capacity = capacity_map.get(resource_key)
            if capacity is None:
                continue
            prob += pulp.lpSum(terms) <= capacity, f"{label}_Capacity_{resource_key}"

    def _extract_results(self, prob, x, over_sla, shipment_options, status_str, elapsed) -> BatchOptimizationResult:
        """Parse the solved PuLP problem into structured, business-readable results."""
        shipment_results = {}
        total_cost = 0.0
        total_baseline_cost = 0.0  # Cost if every shipment had taken the "Delay_Launch" (no-action) path.

        for sid, options in shipment_options.items():
            selected_opt = None
            for opt in options:
                key = (sid, opt.option_name)
                if key in x and pulp.value(x[key]) is not None and pulp.value(x[key]) > 0.5:
                    selected_opt = opt
                    break

            days_over = float(pulp.value(over_sla[sid]) or 0.0)
            penalty_pct = self.late_penalty_pct_lookup.get(sid, LATE_PENALTY_PCT_PER_DAY_DEFAULT)
            order_value = self.order_value_lookup.get(sid, 0.0)
            late_penalty_cost = order_value * penalty_pct * days_over

            carbon_cost = (selected_opt.emission_kg * CARBON_PRICE_PER_KG_USD) if selected_opt else 0.0
            option_cost = selected_opt.cost_usd if selected_opt else 0.0
            shipment_total_cost = option_cost + carbon_cost + late_penalty_cost

            baseline_opt = next((o for o in options if o.option_name == "Delay_Launch"), None)
            baseline_cost = baseline_opt.cost_usd if baseline_opt else shipment_total_cost

            total_cost += shipment_total_cost
            total_baseline_cost += baseline_cost

            shipment_results[sid] = ShipmentOptimizationResult(
                shipment_id=sid,
                selected_option=selected_opt,
                all_options=options,
                days_over_sla=days_over,
                late_penalty_cost=round(late_penalty_cost, 2),
                carbon_cost=round(carbon_cost, 2),
                total_cost=round(shipment_total_cost, 2),
            )

        savings = round(total_baseline_cost - total_cost, 2)

        return BatchOptimizationResult(
            status=status_str,
            total_cost_usd=round(total_cost, 2),
            total_savings_usd=savings,
            shipment_results=shipment_results,
            solver_time_seconds=round(elapsed, 4),
        )
