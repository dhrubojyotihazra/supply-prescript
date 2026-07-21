from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from api.database import engine as db_engine, Base, get_db
import api.models as models
import api.schemas as schemas
from engine.predictive import predict_delay_risk

# Auto-create tables in Supabase PostgreSQL
Base.metadata.create_all(bind=db_engine)

app = FastAPI(
    title="SupplyPrescript API",
    description="Closed-Loop Prescriptive Analytics Write-Back API",
    version="1.0.0"
)

# Enable CORS for React UI & Retool Frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
def get_warehouses(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    db: Session = Depends(get_db)
):
    warehouses = db.query(models.Warehouse).offset(skip).limit(limit).all()
    return warehouses

@app.post("/predict")
def predict_delay(features: dict):
    """
    Accepts warehouse attributes and calculates delay risk using trained XGBoost baseline model.
    """
    try:
        result = predict_delay_risk(features)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
