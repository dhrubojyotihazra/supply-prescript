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
    analyst_notes: Optional[str] = None


class DecisionResponse(DecisionCreate):
    id: int
    analyst_notes: Optional[str] = None
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


class IncidentLogResponse(BaseModel):
    id: int
    incident_code: str
    pipeline_node: str
    error_rate: float
    threshold: float
    status: str
    trigger_reason: str
    dlq_table_name: str
    pre_anomaly_snapshot_id: Optional[str] = None
    paused_at: datetime
    resumed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class StreamSimulationRequest(BaseModel):
    error_rate_percent: float = 4.5
    pipeline_node: Optional[str] = "FLINK_CONNECTOR_01"


class TimeTravelQueryRequest(BaseModel):
    snapshot_id: str = "snap-1002"


class RollbackRequest(BaseModel):
    snapshot_id: str = "snap-1002"

