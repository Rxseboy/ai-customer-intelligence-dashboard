import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# Adjust path to find src
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.insert(0, PROJECT_ROOT)

from src.back_end.api.services.analytics_service import AnalyticsService
from src.back_end.ml.data_loader import get_engine

engine = get_engine()

print("Starting Audit Validator...")

def get_db_dates():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT MIN(order_date)::date, MAX(order_date)::date FROM fact_orders")).fetchone()
        return str(res[0]), str(res[1])

D_FROM, D_TO = get_db_dates()
print(f"Data Date Range: {D_FROM} to {D_TO}")

def audit_revenue_overview():
    print("\n====================================")
    print("MODULE 1: REVENUE OVERVIEW")
    print("====================================")
    
    with engine.connect() as conn:
        df = pd.read_sql(f"SELECT customer_id, order_id, sale_price, status FROM fact_orders WHERE status NOT IN ('Cancelled', 'Returned') AND order_date >= '{D_FROM}' AND order_date < '{D_TO}'::DATE + INTERVAL '1 day'", conn)
        
    actual_revenue = df['sale_price'].sum()
    actual_orders = df['order_id'].nunique()
    actual_customers = df['customer_id'].nunique()
    actual_aov = actual_revenue / actual_orders if actual_orders > 0 else 0
    
    kpis = AnalyticsService.get_kpis(d_from=D_FROM, d_to=D_TO)
    app_revenue = kpis.get('revenue', 0)
    app_orders = kpis.get('orders', 0)
    app_customers = kpis.get('customers', 0)
    app_aov = kpis.get('aov', 0)
    
    print(f"Revenue   | Ground Truth: {actual_revenue:.2f} | App: {app_revenue:.2f} | {'PASS' if abs(actual_revenue - app_revenue) < 1 else 'FAIL'}")
    print(f"Orders    | Ground Truth: {actual_orders} | App: {app_orders} | {'PASS' if actual_orders == app_orders else 'FAIL'}")
    print(f"Customers | Ground Truth: {actual_customers} | App: {app_customers} | {'PASS' if actual_customers == app_customers else 'FAIL'}")
    print(f"AOV       | Ground Truth: {actual_aov:.2f} | App: {app_aov:.2f} | {'PASS' if abs(actual_aov - app_aov) < 1 else 'FAIL'}")

def audit_pareto():
    print("\n====================================")
    print("MODULE 2: PARETO ANALYSIS (80/20)")
    print("====================================")
    
    with engine.connect() as conn:
        df = pd.read_sql(f"SELECT customer_id, SUM(sale_price) as clv FROM fact_orders WHERE status NOT IN ('Cancelled', 'Returned') AND order_date >= '{D_FROM}' AND order_date < '{D_TO}'::DATE + INTERVAL '1 day' GROUP BY customer_id", conn)
    
    df = df.sort_values('clv', ascending=False)
    top_20_count = int(len(df) * 0.20)
    top_20_revenue = df.head(top_20_count)['clv'].sum()
    total_revenue = df['clv'].sum()
    
    actual_pareto_pct = (top_20_revenue / total_revenue) * 100 if total_revenue > 0 else 0
    
    insights = AnalyticsService.get_insights(d_from=D_FROM, d_to=D_TO)
    app_pareto_pct = insights.get('pareto_top20_pct', 0)
    
    print(f"Pareto %  | Ground Truth: {actual_pareto_pct:.1f}% | App: {app_pareto_pct:.1f}% | {'PASS' if abs(actual_pareto_pct - app_pareto_pct) < 0.2 else 'FAIL'}")

def audit_churn_metrics():
    print("\n====================================")
    print("MODULE 3: CHURN ANALYTICS")
    print("====================================")
    
    with engine.connect() as conn:
        query = text(f"""
            SELECT customer_id, 
                   ('{D_TO}'::DATE - MAX(order_date)::DATE) as recency
            FROM fact_orders 
            WHERE status NOT IN ('Cancelled', 'Returned')
              AND order_date >= '{D_FROM}' AND order_date < '{D_TO}'::DATE + INTERVAL '1 day'
            GROUP BY customer_id
        """)
        df = pd.read_sql(query, conn)
        
    total_cust = len(df)
    churned_cust = len(df[df['recency'] > 90])
    actual_churn_rate = (churned_cust / total_cust) * 100 if total_cust > 0 else 0
    
    insights = AnalyticsService.get_insights(d_from=D_FROM, d_to=D_TO)
    app_churn_rate = insights.get('churn_rate_pct', 0)
    
    print(f"Churn Rate| Ground Truth: {actual_churn_rate:.1f}% | App: {app_churn_rate:.1f}% | {'PASS' if abs(actual_churn_rate - app_churn_rate) < 0.2 else 'FAIL'}")

def audit_product_analytics():
    print("\n====================================")
    print("MODULE 4: PRODUCT ANALYTICS")
    print("====================================")
    with engine.connect() as conn:
        df = pd.read_sql(f"""
            SELECT p.category, SUM(fo.sale_price) as rev 
            FROM fact_orders fo
            JOIN dim_products p ON fo.product_id = p.product_id
            WHERE fo.status NOT IN ('Cancelled', 'Returned')
              AND fo.order_date >= '{D_FROM}' AND fo.order_date < '{D_TO}'::DATE + INTERVAL '1 day'
            GROUP BY p.category
            ORDER BY rev DESC LIMIT 5
        """, conn)
    
    actual_top_cat = df.iloc[0]['category'] if not df.empty else None
    actual_top_rev = df.iloc[0]['rev'] if not df.empty else 0
    
    res = AnalyticsService.get_products(d_from=D_FROM, d_to=D_TO, limit=5)
    cats = res.get('products', [])
    app_top_cat = cats[0]['category'] if cats else None
    app_top_rev = cats[0]['revenue'] if cats else 0
    
    print(f"Top Categ | Ground Truth: {actual_top_cat} | App: {app_top_cat} | {'PASS' if actual_top_cat == app_top_cat else 'FAIL'}")
    print(f"Top C Rev | Ground Truth: {actual_top_rev:.2f} | App: {app_top_rev:.2f} | {'PASS' if abs(actual_top_rev - app_top_rev) < 1 else 'FAIL'}")

def run_all():
    audit_revenue_overview()
    audit_pareto()
    audit_churn_metrics()
    audit_product_analytics()
    print("\nAudit Complete.")

if __name__ == "__main__":
    run_all()
