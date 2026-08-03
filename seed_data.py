import pandas as pd
from api.database import SessionLocal, engine
import api.models as models

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

count = db.query(models.Warehouse).count()
if count == 0:
    print("Seeding warehouse data from FMCG_data.csv...")
    df = pd.read_csv("data/FMCG_data.csv")

    warehouses = []
    for idx, row in df.iterrows():
        wh_id = str(row.get('Warehouse_ID', row.get('Ware_house_ID', f"WH_{idx+100000}")))
        loc_type = str(row.get('Location_type', 'Urban'))
        cap_size = str(row.get('WH_capacity_size', row.get('Capacity', 'Medium')))
        zone_val = str(row.get('zone', 'North'))
        workers = float(row.get('workers_num', 45.0))
        dist = float(row.get('dist_from_hub', 12.5))
        trans_issue = int(row.get('transport_issue_l1y', row.get('Delivery_Time_Days', 0)))
        wh_break = int(row.get('wh_breakdown_l3m', 0))
        prod_wg = float(row.get('product_wg_ton', row.get('Demand', 100.0)))
        status_val = "Delayed" if trans_issue > 2 else "Normal"

        wh = models.Warehouse(
            warehouse_id=wh_id,
            location_type=loc_type,
            capacity_size=cap_size,
            zone=zone_val,
            workers_num=workers,
            dist_from_hub=dist,
            transport_issue_l1y=trans_issue,
            wh_breakdown_l3m=wh_break,
            product_wg_ton=prod_wg,
            status=status_val
        )
        warehouses.append(wh)
    
    db.bulk_save_objects(warehouses)
    db.commit()
    print(f"Successfully seeded {len(warehouses)} warehouses into database!")
else:
    print(f"Warehouses table already contains {count} records.")

db.close()

