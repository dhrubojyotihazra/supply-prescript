"""
cost_function.py
=================

SupplyPrescript - Week 2 Prescriptive Analytics Engine
Cost-function library: translates a shipment's context + reference data
into the fully-costed candidate mitigation options consumed by the MILP
optimizer.

Each candidate option bundles every cost component named in the Week-2
objective function (transportation, supplier premium, inventory/holding,
storage, carbon, production-delay) into a single per-option cost, plus the
resulting expected delay and the resource it consumes (for capacity
constraints).

Author: SupplyPrescript ML Engineering Team
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("cost_function")

CARBON_PRICE_PER_KG_USD = 0.08  # Internal carbon price used to cost CO2 in the objective.


@dataclass
class MitigationOption:
    """A single fully-costed candidate action for one shipment."""

    shipment_id: str
    option_name: str                  # e.g. "Air_Freight", "Secondary_Supplier"
    cost_usd: float                   # Total bundled cost of choosing this option
    expected_delay_days: float        # Residual delay if this option is chosen
    emission_kg: float
    resource_type: Optional[str] = None      # "transport_mode", "supplier", "inventory", "production"
    resource_key: Optional[str] = None       # e.g. "Air", supplier_id, warehouse_id, production_id
    resource_units_required: float = 0.0     # Units/kg consumed of that resource
    feasible: bool = True
    infeasibility_reason: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class CostFunctionEngine:
    """
    Builds the full candidate-option set (with bundled costs) for a shipment,
    given the Week-2 reference tables (suppliers, transportation, inventory,
    warehouse, production schedule, customer orders).
    """

    def __init__(
        self,
        suppliers: pd.DataFrame,
        supplier_capacity: pd.DataFrame,
        transportation_cost: pd.DataFrame,
        shipping_options: pd.DataFrame,
        inventory: pd.DataFrame,
        warehouse: pd.DataFrame,
        production_schedule: pd.DataFrame,
        customer_orders: pd.DataFrame,
    ):
        self.suppliers = suppliers
        self.supplier_capacity = supplier_capacity
        self.transportation_cost = transportation_cost.set_index("Mode")
        self.shipping_options = shipping_options
        self.inventory = inventory
        self.warehouse = warehouse
        self.production_schedule = production_schedule
        self.customer_orders = customer_orders.set_index("Shipment_ID")

    # ------------------------------------------------------------------
    def _lane_option(self, origin: str, destination: str, mode: str) -> Optional[pd.Series]:
        rows = self.shipping_options[
            (self.shipping_options["Origin_Country"] == origin)
            & (self.shipping_options["Destination_Country"] == destination)
            & (self.shipping_options["Mode"] == mode)
        ]
        if rows.empty:
            return None
        return rows.iloc[0]

    def _transport_cost(self, mode: str, weight_kg: float) -> float:
        rate = self.transportation_cost.loc[mode]
        return float(rate["Base_Fee_USD"] + rate["Cost_Per_Kg_USD"] * weight_kg)

    def _transport_emission(self, mode: str, weight_kg: float) -> float:
        rate = self.transportation_cost.loc[mode]
        return float(rate["CO2_Kg_Per_Kg_Shipped"] * weight_kg)

    # ------------------------------------------------------------------
    def build_options(self, shipment: pd.Series, expected_delay_days: float) -> list[MitigationOption]:
        """
        Build the full candidate mitigation-option list for one shipment.

        Parameters
        ----------
        shipment : pd.Series
            A row from the active shipment batch (must include Shipment_ID,
            Supplier_ID, Supplier_Country, Destination_Country,
            Shipment_Weight, Purchase_Order_Value, Product_Category, Units,
            Warehouse).
        expected_delay_days : float
            The ML-estimated delay (days) if no mitigating action is taken.
        """
        sid = shipment["Shipment_ID"]
        options: list[MitigationOption] = []

        options.append(self._option_transport_mode(shipment, expected_delay_days, "Air"))
        options.append(self._option_transport_mode(shipment, expected_delay_days, "Rail"))
        options.append(self._option_transport_mode(shipment, expected_delay_days, "Sea"))
        options.append(self._option_secondary_supplier(shipment, expected_delay_days))
        options.append(self._option_use_safety_stock(shipment, expected_delay_days))
        options.append(self._option_expedite_manufacturing(shipment, expected_delay_days))
        options.append(self._option_delay_launch(shipment, expected_delay_days))

        return [o for o in options if o is not None]

    # ------------------------------------------------------------------
    def _option_transport_mode(self, shipment: pd.Series, base_delay: float, mode: str) -> MitigationOption:
        sid = shipment["Shipment_ID"]
        origin, destination = shipment["Supplier_Country"], shipment["Destination_Country"]
        weight = float(shipment["Shipment_Weight"])
        lane = self._lane_option(origin, destination, mode)

        if lane is None or not bool(lane["Available"]):
            return MitigationOption(
                shipment_id=sid, option_name=f"{mode}_Freight", cost_usd=np.inf,
                expected_delay_days=base_delay, emission_kg=0.0,
                resource_type="transport_mode", resource_key=mode,
                feasible=False, infeasibility_reason=f"No available {mode} lane for {origin}->{destination}.",
            )

        cost = self._transport_cost(mode, weight)
        emission = self._transport_emission(mode, weight)
        # Residual delay after switching mode: whichever is smaller of the lane's
        # transit time (converted to a delay-equivalent) or the original expected delay,
        # modelling that faster modes largely absorb the risk-driven delay.
        speed_factor = {"Air": 0.12, "Rail": 0.55, "Sea": 0.85}[mode]
        residual_delay = round(max(base_delay * speed_factor, 0.0), 1)

        return MitigationOption(
            shipment_id=sid,
            option_name=f"{mode}_Freight",
            cost_usd=round(cost, 2),
            expected_delay_days=residual_delay,
            emission_kg=round(emission, 2),
            resource_type="transport_mode",
            resource_key=mode,
            resource_units_required=weight,
            metadata={"transit_days": float(lane["Transit_Days"]), "lane_capacity_kg": float(lane["Weekly_Capacity_Kg"])},
        )

    def _option_secondary_supplier(self, shipment: pd.Series, base_delay: float) -> Optional[MitigationOption]:
        sid = shipment["Shipment_ID"]
        primary_id = shipment["Supplier_ID"]
        sup_row = self.suppliers[self.suppliers["Supplier_ID"] == primary_id]
        if sup_row.empty or pd.isna(sup_row.iloc[0].get("Secondary_Supplier_ID")):
            return None
        sup_row = sup_row.iloc[0]
        secondary_id = sup_row["Secondary_Supplier_ID"]
        premium_pct = float(sup_row["Secondary_Premium_Pct"])
        order_value = float(shipment["Purchase_Order_Value"])
        units = int(shipment.get("Units", 1))

        cap_row = self.supplier_capacity[
            (self.supplier_capacity["Supplier_ID"] == secondary_id)
            & (self.supplier_capacity["Product_Category"] == shipment.get("Product_Category"))
        ]
        available_capacity = float(cap_row["Available_Capacity_Units"].iloc[0]) if not cap_row.empty else 0.0
        feasible = available_capacity >= units

        cost = order_value * premium_pct
        secondary_lead_time = float(
            self.suppliers.loc[self.suppliers["Supplier_ID"] == secondary_id, "Lead_Time_Days"].iloc[0]
        )
        residual_delay = round(min(base_delay, max(secondary_lead_time - shipment.get("Expected_Lead_Time", secondary_lead_time), 0)), 1)

        return MitigationOption(
            shipment_id=sid,
            option_name="Secondary_Supplier",
            cost_usd=round(cost, 2),
            expected_delay_days=residual_delay,
            emission_kg=0.0,
            resource_type="supplier",
            resource_key=str(secondary_id),
            resource_units_required=units,
            feasible=feasible,
            infeasibility_reason=None if feasible else "Insufficient secondary supplier capacity.",
            metadata={"premium_pct": premium_pct, "available_capacity": available_capacity},
        )

    def _option_use_safety_stock(self, shipment: pd.Series, base_delay: float) -> Optional[MitigationOption]:
        sid = shipment["Shipment_ID"]
        warehouse_id = shipment.get("Warehouse")
        category = shipment.get("Product_Category")
        units = int(shipment.get("Units", 1))

        inv_row = self.inventory[
            (self.inventory["Warehouse_ID"] == warehouse_id) & (self.inventory["Product_Category"] == category)
        ]
        if inv_row.empty:
            return None
        inv_row = inv_row.iloc[0]
        usable_stock = float(inv_row["Usable_Safety_Stock_Units"])
        holding_cost_per_unit = float(inv_row["Holding_Cost_Per_Unit_USD"])
        feasible = usable_stock >= units

        cost = holding_cost_per_unit * units * 3  # accelerated draw-down premium (3x normal holding cost)
        return MitigationOption(
            shipment_id=sid,
            option_name="Use_Safety_Stock",
            cost_usd=round(cost, 2),
            expected_delay_days=0.0,  # Safety stock ships immediately from on-hand inventory.
            emission_kg=0.0,
            resource_type="inventory",
            resource_key=f"{warehouse_id}|{category}",
            resource_units_required=units,
            feasible=feasible,
            infeasibility_reason=None if feasible else "Insufficient usable safety stock.",
            metadata={"usable_stock": usable_stock},
        )

    def _option_expedite_manufacturing(self, shipment: pd.Series, base_delay: float) -> Optional[MitigationOption]:
        sid = shipment["Shipment_ID"]
        category = shipment.get("Product_Category")
        units = int(shipment.get("Units", 1))

        prod_rows = self.production_schedule[
            (self.production_schedule["Product_Category"] == category)
            & (self.production_schedule["Can_Expedite"])
        ]
        if prod_rows.empty:
            return None
        prod = prod_rows.iloc[0]
        expedite_cost_per_unit = float(prod["Expedite_Cost_Per_Unit_USD"])
        max_expedite_days = float(prod["Max_Expedite_Days"])
        daily_capacity = float(prod["Daily_Capacity_Units"])
        feasible = units <= daily_capacity * 3  # assume up to 3 days of capacity can be pooled

        cost = expedite_cost_per_unit * units
        residual_delay = round(max(base_delay - max_expedite_days, 0.0), 1)

        return MitigationOption(
            shipment_id=sid,
            option_name="Expedite_Manufacturing",
            cost_usd=round(cost, 2),
            expected_delay_days=residual_delay,
            emission_kg=0.0,
            resource_type="production",
            resource_key=str(prod["Production_ID"]),
            resource_units_required=units,
            feasible=feasible,
            infeasibility_reason=None if feasible else "Exceeds pooled production line capacity.",
            metadata={"max_expedite_days": max_expedite_days},
        )

    def _option_delay_launch(self, shipment: pd.Series, base_delay: float) -> MitigationOption:
        """
        The 'do nothing / accept the delay' option: no transportation or
        supplier cost, but the business absorbs a revenue-loss / late-penalty
        cost proportional to order value and days late beyond SLA.
        """
        sid = shipment["Shipment_ID"]
        order_value = float(shipment["Purchase_Order_Value"])

        sla_days = 8
        penalty_pct_per_day = 0.012
        try:
            order_row = self.customer_orders.loc[sid]
            sla_days = float(order_row["SLA_Max_Delay_Days"])
            penalty_pct_per_day = float(order_row["Late_Penalty_Pct_Per_Day"])
        except KeyError:
            pass

        days_over_sla = max(base_delay - sla_days, 0.0)
        revenue_loss = order_value * penalty_pct_per_day * days_over_sla

        return MitigationOption(
            shipment_id=sid,
            option_name="Delay_Launch",
            cost_usd=round(revenue_loss, 2),
            expected_delay_days=base_delay,
            emission_kg=0.0,
            resource_type=None,
            resource_key=None,
            resource_units_required=0.0,
            metadata={"sla_days": sla_days, "days_over_sla": days_over_sla},
        )
