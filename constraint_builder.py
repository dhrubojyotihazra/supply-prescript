"""
constraint_builder.py
======================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Builds the resource-capacity and business-policy constraint parameters that
the PuLP MILP model enforces across a batch of shipments being jointly
optimized.

Constraints modelled
---------------------
    * Budget            - total spend across all selected options
    * Transportation    - weekly capacity (kg) per transport mode/lane
    * Supplier capacity - available units per (secondary) supplier
    * Inventory          - usable safety-stock units per warehouse/category
    * Production          - pooled daily capacity per expedite-capable line
    * Warehouse capacity - available storage units per warehouse
    * Maximum acceptable delay / Customer SLA - per-shipment, priority-aware
    * Carbon emission limit - total CO2 budget for the optimization run

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

logger = logging.getLogger("constraint_builder")


@dataclass
class OptimizationConstraints:
    """Container for all resource limits used by a single optimization run."""

    budget_usd: float
    carbon_limit_kg: float
    transport_capacity_kg: dict = field(default_factory=dict)     # {mode: capacity_kg}
    supplier_capacity_units: dict = field(default_factory=dict)   # {supplier_id: available_units}
    inventory_capacity_units: dict = field(default_factory=dict)  # {"warehouse|category": usable_units}
    production_capacity_units: dict = field(default_factory=dict)  # {production_id: pooled_capacity_units}
    warehouse_capacity_units: dict = field(default_factory=dict)  # {warehouse_id: available_units}
    sla_days: dict = field(default_factory=dict)                  # {shipment_id: sla_days}
    hard_sla_priorities: tuple = ("Critical", "High")             # priorities where SLA is a hard constraint


class ConstraintBuilder:
    """
    Derives an :class:`OptimizationConstraints` instance from the Week-2
    reference tables for a given batch of shipments.
    """

    def __init__(
        self,
        shipping_options: pd.DataFrame,
        supplier_capacity: pd.DataFrame,
        inventory: pd.DataFrame,
        warehouse: pd.DataFrame,
        production_schedule: pd.DataFrame,
        customer_orders: pd.DataFrame,
    ):
        self.shipping_options = shipping_options
        self.supplier_capacity = supplier_capacity
        self.inventory = inventory
        self.warehouse = warehouse
        self.production_schedule = production_schedule
        self.customer_orders = customer_orders

    def build(
        self,
        shipment_ids: list[str],
        budget_usd: float,
        carbon_limit_kg: float,
    ) -> OptimizationConstraints:
        """Build the constraint set for the given batch of shipment IDs."""
        transport_capacity_kg = (
            self.shipping_options.groupby("Mode")["Weekly_Capacity_Kg"].sum().to_dict()
        )

        supplier_capacity_units = (
            self.supplier_capacity.groupby("Supplier_ID")["Available_Capacity_Units"].sum().to_dict()
        )

        inventory_capacity_units = {
            f"{row.Warehouse_ID}|{row.Product_Category}": row.Usable_Safety_Stock_Units
            for row in self.inventory.itertuples()
        }

        production_capacity_units = {
            row.Production_ID: row.Daily_Capacity_Units * 3  # pooled 3-day expedite window
            for row in self.production_schedule.itertuples()
            if row.Can_Expedite
        }

        warehouse_capacity_units = (
            self.warehouse.set_index("Warehouse_ID")["Available_Capacity_Units"].to_dict()
        )

        orders = self.customer_orders.set_index("Shipment_ID")
        sla_days = {}
        for sid in shipment_ids:
            if sid in orders.index:
                sla_days[sid] = float(orders.loc[sid, "SLA_Max_Delay_Days"])
            else:
                sla_days[sid] = 8.0  # sensible default SLA if no matching order record

        constraints = OptimizationConstraints(
            budget_usd=budget_usd,
            carbon_limit_kg=carbon_limit_kg,
            transport_capacity_kg=transport_capacity_kg,
            supplier_capacity_units=supplier_capacity_units,
            inventory_capacity_units=inventory_capacity_units,
            production_capacity_units=production_capacity_units,
            warehouse_capacity_units=warehouse_capacity_units,
            sla_days=sla_days,
        )
        logger.info(
            "Built constraints for %d shipments. Budget=$%.0f, Carbon limit=%.0fkg.",
            len(shipment_ids), budget_usd, carbon_limit_kg,
        )
        return constraints
