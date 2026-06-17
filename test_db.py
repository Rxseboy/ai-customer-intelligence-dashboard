import os
import sys
from sqlalchemy import text
sys.path.insert(0, os.path.abspath('.'))
from src.back_end.ml.data_loader import get_engine
engine = get_engine()
with engine.connect() as conn:
    res = conn.execute(text("SELECT MIN(order_date), MAX(order_date) FROM fact_orders")).fetchone()
    print('Min date:', res[0])
    print('Max date:', res[1])
