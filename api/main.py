from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from api.database import engine, Base, get_db
import api.models as models
import api.schemas as schemas

# Auto-create tables in Supabase PostgreSQL
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SupplyPrescript API",
    description="Closed-Loop Prescriptive Analytics Write-Back API",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "SupplyPrescript Backend API",
        "database": "Connected to Supabase PostgreSQL"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/warehouses", response_model=List[schemas.WarehouseBase])
def get_warehouses(db: Session = Depends(get_db)):
    warehouses = db.query(models.Warehouse).all()
    return warehouses

@app.post("/execute-decision", response_model=schemas.DecisionResponse, status_code=status.HTTP_201_CREATED)
def execute_decision(decision: schemas.DecisionCreate, db: Session = Depends(get_db)):
    db_decision = models.Decision(
        warehouse_id=decision.warehouse_id,
        selected_option=decision.selected_option,
        prescribed_cost=decision.prescribed_cost,
        expected_delay_days=decision.expected_delay_days
    )
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)
    return db_decision

@app.post("/log-outcome", response_model=schemas.OutcomeResponse, status_code=status.HTTP_201_CREATED)
def log_outcome(outcome: schemas.OutcomeCreate, db: Session = Depends(get_db)):
    # Verify decision exists
    decision = db.query(models.Decision).filter(models.Decision.id == outcome.decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision record not found")

    db_outcome = models.Outcome(
        decision_id=outcome.decision_id,
        actual_cost=outcome.actual_cost,
        actual_delay_days=outcome.actual_delay_days
    )
    db.add(db_outcome)
    db.commit()
    db.refresh(db_outcome)
    return db_outcome
