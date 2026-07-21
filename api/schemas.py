from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class WarehouseBase(BaseModel):
    warehouse_id: str
    location_type: Optional[str] = None
    capacity_size: Optional[str] = None
    zone: Optional[str] = None
    workers_num: Optional[float] = None
    dist_from_hub: Optional[float] = None
    transport_issue_l1y: Optional[int] = None
    wh_breakdown_l3m: Optional[int] = None
    product_wg_ton: Optional[float] = None
    status: Optional[str] = "Normal"

    class Config:
        from_attributes = True


class DecisionCreate(BaseModel):
    warehouse_id: str
    selected_option: str
    prescribed_cost: float
    expected_delay_days: int


class DecisionResponse(DecisionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class OutcomeCreate(BaseModel):
    decision_id: int
    actual_cost: float
    actual_delay_days: int


class OutcomeResponse(OutcomeCreate):
    id: int
    evaluated_at: datetime

    class Config:
        from_attributes = True
