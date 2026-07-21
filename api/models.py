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
