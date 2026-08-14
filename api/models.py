from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from api.database import Base

class Warehouse(Base):
    __tablename__ = "warehouses"

    warehouse_id = Column(String, primary_key=True, index=True)
    location_type = Column(String, nullable=True)
    capacity_size = Column(String, nullable=True)
    zone = Column(String, nullable=True)
    workers_num = Column(Float, nullable=True)
    dist_from_hub = Column(Float, nullable=True)
    transport_issue_l1y = Column(Integer, nullable=True)
    wh_breakdown_l3m = Column(Integer, nullable=True)
    product_wg_ton = Column(Float, nullable=True)
    status = Column(String, default="Normal")

    decisions = relationship("Decision", back_populates="warehouse")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    warehouse_id = Column(String, ForeignKey("warehouses.warehouse_id"), nullable=False)
    selected_option = Column(String, nullable=False)
    prescribed_cost = Column(Float, nullable=False)
    expected_delay_days = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    warehouse = relationship("Warehouse", back_populates="decisions")
    outcome = relationship("Outcome", uselist=False, back_populates="decision")


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    actual_cost = Column(Float, nullable=False)
    actual_delay_days = Column(Integer, nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    decision = relationship("Decision", back_populates="outcome")


class IncidentLog(Base):
    __tablename__ = "incident_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_code = Column(String, nullable=False, unique=True, index=True)
    pipeline_node = Column(String, nullable=False, default="FLINK_CONNECTOR_01")
    error_rate = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False, default=2.0)
    status = Column(String, nullable=False, default="TRIPPED_ROUTED_DLQ") # TRIPPED_ROUTED_DLQ, RESOLVED, ROLLED_BACK
    trigger_reason = Column(String, nullable=False)
    dlq_table_name = Column(String, nullable=False, default="warehouses_dlq_stream")
    pre_anomaly_snapshot_id = Column(String, nullable=True, default="snap-1002")
    paused_at = Column(DateTime, default=datetime.utcnow)
    resumed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)


class IcebergSnapshotRecord(Base):
    __tablename__ = "iceberg_snapshot_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    snapshot_id = Column(String, nullable=False, unique=True, index=True)
    table_name = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    parent_snapshot_id = Column(String, nullable=True)
    record_count = Column(Integer, nullable=False, default=0)
    commit_summary = Column(String, nullable=False)
    status = Column(String, nullable=False, default="VALID")
    is_current = Column(Integer, default=1)

