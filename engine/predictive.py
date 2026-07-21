import os
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

MODEL_PATH = os.path.join(os.path.dirname(__file__), "xgboost_model.joblib")

def train_predictive_model():
    print("Loading FMCG_data.csv for ML training...")
    df = pd.read_csv("data/FMCG_data.csv")

    # Target: Flag delay if transport_issue_l1y > 2
    df['is_delayed'] = (df['transport_issue_l1y'] > 2).astype(int)

    # Feature selection
    feature_cols = ['dist_from_hub', 'workers_num', 'product_wg_ton', 
                    'wh_breakdown_l3m', 'num_refill_req_l3m', 'Competitor_in_mkt']
    
    # Clean missing values
    X = df[feature_cols].fillna(0)
    y = df['is_delayed']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"XGBoost Baseline Model Accuracy: {acc * 100:.2f}%")

    # Save model artifact
    joblib.dump(model, MODEL_PATH)
    print(f"Saved trained XGBoost model to {MODEL_PATH}")
    return model

def predict_delay_risk(features: dict) -> dict:
    if not os.path.exists(MODEL_PATH):
        train_predictive_model()
    
    model = joblib.load(MODEL_PATH)
    
    # Construct input dataframe
    input_data = pd.DataFrame([{
        'dist_from_hub': features.get('dist_from_hub', 0),
        'workers_num': features.get('workers_num', 0),
        'product_wg_ton': features.get('product_wg_ton', 0),
        'wh_breakdown_l3m': features.get('wh_breakdown_l3m', 0),
        'num_refill_req_l3m': features.get('num_refill_req_l3m', 0),
        'Competitor_in_mkt': features.get('Competitor_in_mkt', 0)
    }])

    prob = float(model.predict_proba(input_data)[0][1])
    is_high_risk = bool(prob > 0.4)

    return {
        "delay_probability": round(prob, 4),
        "is_high_risk": is_high_risk,
        "recommended_action_needed": is_high_risk
    }

if __name__ == "__main__":
    train_predictive_model()
