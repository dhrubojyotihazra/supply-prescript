import pandas as pd
from api.database import SessionLocal, engine
import api.models as models

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

count = db.query(models.Warehouse).count()
if count == 0:
    print("Seeding warehouse data from FMCG_data.csv...")
    df = pd.read_csv("data/FMCG_data.csv")
    
    df_clean = df.fillna({
        'Location_type': 'Unknown',
        'WH_capacity_size': 'Unknown',
        'zone': 'Unknown',
        'workers_num': 0,
        'dist_from_hub': 0,
        'transport_issue_l1y': 0,
        'wh_breakdown_l3m': 0,
        'product_wg_ton': 0
    })

    warehouses = []
    for _, row in df_clean.iterrows():
        wh = models.Warehouse(
            warehouse_id=str(row['Ware_house_ID']),
            location_type=str(row['Location_type']),
            capacity_size=str(row['WH_capacity_size']),
            zone=str(row['zone']),
            workers_num=float(row['workers_num']),
            dist_from_hub=float(row['dist_from_hub']),
            transport_issue_l1y=int(row['transport_issue_l1y']),
            wh_breakdown_l3m=int(row['wh_breakdown_l3m']),
            product_wg_ton=float(row['product_wg_ton']),
            status="Delayed" if int(row['transport_issue_l1y']) > 2 else "Normal"
        )
        warehouses.append(wh)
    
    db.bulk_save_objects(warehouses)
    db.commit()
    print(f"Successfully seeded {len(warehouses)} warehouses into Supabase PostgreSQL!")
else:
    print(f"Warehouses table already contains {count} records.")

db.close()
