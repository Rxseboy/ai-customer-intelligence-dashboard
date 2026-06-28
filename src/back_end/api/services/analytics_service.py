import json
from datetime import datetime
from sqlalchemy import text
from src.back_end.ml.data_loader import get_engine

class AnalyticsService:
    @staticmethod
    def _build_segment_cte(segments: str = None) -> tuple[str, str]:
        if not segments:
            return "", ""
        
        seg_list = [s.strip() for s in segments.split(",") if s.strip()]
        if not seg_list:
            return "", ""
            
        formatted_segs = ", ".join(f"'{s}'" for s in seg_list)
        
        cte = f"""WITH segment_calc_base AS (
            SELECT customer_id,
                   COUNT(DISTINCT order_id) AS frequency,
                   ROUND(SUM(sale_price)::numeric, 2) AS monetary,
                   (CAST(:d2 AS DATE) - MAX(order_date)::date) AS recency
            FROM fact_orders
            WHERE status NOT IN ('Cancelled', 'Returned')
              AND order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
            GROUP BY customer_id
        ),
        segment_calc_ranked AS (
            SELECT customer_id,
                   NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
                   NTILE(5) OVER (ORDER BY frequency ASC, recency DESC) AS f_score,
                   NTILE(5) OVER (ORDER BY monetary ASC, recency DESC) AS m_score
            FROM segment_calc_base
        ),
        segment_calc_segmented AS (
            SELECT customer_id,
                   CASE
                       WHEN (r_score + f_score + m_score) >= 13 THEN 'Champion'
                       WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal'
                       WHEN (r_score + f_score + m_score) >=  7 THEN 'Potential'
                       WHEN (r_score + f_score + m_score) >=  4 THEN 'At Risk'
                       ELSE 'Lost'
                   END AS segment_key
            FROM segment_calc_ranked
        ),
        filtered_customers AS (
            SELECT customer_id
            FROM segment_calc_segmented
            WHERE segment_key IN ({formatted_segs})
        )"""
        
        join_clause = " JOIN filtered_customers USING (customer_id) "
        return cte, join_clause

    @classmethod
    def get_insights(cls, d_from: str, d_to: str, segments: str = None) -> dict:
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)
            if cte:
                cte = cte + ", customer_stats AS ("
            else:
                cte = "WITH customer_stats AS ("
                
            sql = cte + """
                    SELECT customer_id,
                           SUM(sale_price) AS monetary,
                           (CAST(:d2 AS DATE) - MAX(order_date)::date) AS recency,
                           CASE WHEN (CAST(:d2 AS DATE) - MAX(order_date)::date) > 90 THEN 1.0 ELSE 0.0 END AS is_churn
                    FROM fact_orders
            """ + join_clause + """
                    WHERE order_date >= CAST(:d1 AS DATE) AND order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                      AND status NOT IN ('Cancelled','Returned')
                    GROUP BY customer_id
                ),
                ranked AS (
                    SELECT monetary,
                           PERCENT_RANK() OVER (ORDER BY monetary DESC) as pct_rank
                    FROM customer_stats
                ),
                pareto AS (
                    SELECT COALESCE(SUM(monetary), 0) as top20_rev
                    FROM ranked
                    WHERE pct_rank <= 0.2
                )
                SELECT 
                    COUNT(*) as total_customers,
                    COALESCE(SUM(monetary), 0) as total_revenue,
                    COALESCE(AVG(monetary), 0) as avg_monetary,
                    COALESCE(AVG(recency), 0) as avg_recency,
                    COALESCE(AVG(is_churn) * 100, 0) as churn_rate,
                    (SELECT top20_rev FROM pareto) as top20_rev
                FROM customer_stats
            """
            
            with engine.connect() as conn:
                res = conn.execute(text(sql), {"d1": d_from, "d2": d_to}).fetchone()
                
                if res and res[0] > 0:
                    t_cust = res[0]
                    t_rev = res[1]
                    pareto_pct = (res[5] / t_rev * 100) if t_rev > 0 else 0.0
                    
                    return {
                        "total_customers": int(t_cust),
                        "total_revenue": round(float(t_rev), 2),
                        "avg_monetary": round(float(res[2]), 2),
                        "avg_recency_days": round(float(res[3]), 1),
                        "churn_rate_pct": round(float(res[4]), 1),
                        "pareto_top20_pct": round(float(pareto_pct), 1),
                        "generated_at": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "total_customers": 0, "total_revenue": 0.0, "avg_monetary": 0.0,
                        "avg_recency_days": 0.0, "churn_rate_pct": 0.0, "pareto_top20_pct": 0.0,
                        "generated_at": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            print(f"[AnalyticsService] Error during insights fetch: {e}")
            return {"total_customers": 0, "total_revenue": 0.0, "avg_monetary": 0.0,
                    "avg_recency_days": 0.0, "churn_rate_pct": 0.0, "pareto_top20_pct": 0.0, "generated_at": datetime.utcnow().isoformat()}

    @classmethod
    def get_kpis(cls, d_from: str, d_to: str, segments: str = None) -> dict:
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)

            # Build SQL — single pass to get both revenue KPIs and churn metrics
            if cte:
                cte_prefix = cte + ", orders_base AS ("
            else:
                cte_prefix = "WITH orders_base AS ("

            sql = cte_prefix + """
                SELECT
                    customer_id,
                    order_id,
                    sale_price,
                    order_date,
                    CASE WHEN (CAST(:d2 AS DATE) - MAX(order_date) OVER (PARTITION BY customer_id)::date) > 90
                         THEN 1.0 ELSE 0.0 END AS is_churn
                FROM fact_orders
            """ + join_clause + """
                WHERE order_date >= CAST(:d1 AS DATE)
                  AND order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                  AND status NOT IN ('Cancelled', 'Returned')
            )
            SELECT
                COUNT(DISTINCT customer_id)                                         AS total_customers,
                COUNT(DISTINCT order_id)                                            AS total_orders,
                COALESCE(ROUND(CAST(SUM(sale_price) AS numeric), 2), 0.0)          AS total_revenue,
                COALESCE(ROUND(CAST(SUM(sale_price)
                    / NULLIF(COUNT(DISTINCT order_id), 0) AS numeric), 2), 0.0)    AS aov,
                COALESCE(AVG(is_churn) * 100, 0.0)                                 AS churn_rate_pct
            FROM orders_base
            """
            q = text(sql)
            with engine.connect() as conn:
                row = conn.execute(q, {"d1": d_from, "d2": d_to}).fetchone()
                if row:
                    return {
                        "total_customers":  int(row[0] or 0),
                        "orders":           int(row[1] or 0),
                        "revenue":          float(row[2] or 0.0),
                        "aov":              float(row[3] or 0.0),
                        "churn_rate_pct":   round(float(row[4] or 0.0), 1),
                    }
        except Exception as e:
            print(f"[AnalyticsService] Error during KPIs fetch: {e}")
        return {
            "total_customers": 0, "orders": 0, "revenue": 0.0,
            "aov": 0.0, "churn_rate_pct": 0.0,
        }


    @classmethod
    def get_trend(cls, d_from: str, d_to: str, granularity: str = "Monthly", segments: str = None) -> dict:
        trunc = "month" if granularity.lower() == "monthly" else "week"
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)
            sql = cte + f"""
                SELECT DATE_TRUNC('{trunc}', order_date) AS period,
                       ROUND(SUM(sale_price)::numeric,2) AS revenue,
                       COUNT(DISTINCT order_id)           AS orders
                FROM fact_orders
            """ + join_clause + f"""
                WHERE order_date >= CAST(:d1 AS DATE) AND order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                  AND status NOT IN ('Cancelled','Returned')
                GROUP BY 1 ORDER BY 1
            """
            q = text(sql)
            with engine.connect() as conn:
                res = conn.execute(q, {"d1": d_from, "d2": d_to})
                data = []
                for r in res:
                    data.append({
                        "period": str(r[0].date()) if hasattr(r[0], "date") else str(r[0]),
                        "revenue": float(r[1] or 0.0),
                        "orders": int(r[2] or 0)
                    })
                return {"granularity": granularity, "trend": data}
        except Exception as e:
            print(f"[AnalyticsService] Error during trend fetch: {e}")
        return {"granularity": granularity, "trend": []}

    @classmethod
    def get_status_breakdown(cls, d_from: str, d_to: str, segments: str = None) -> dict:
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)
            sql = cte + """
                SELECT status, COUNT(*) AS cnt,
                       ROUND(SUM(sale_price)::numeric,2) AS revenue
                FROM fact_orders 
            """ + join_clause + """
                WHERE order_date >= CAST(:d1 AS DATE) AND order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                GROUP BY status ORDER BY revenue DESC
            """
            q = text(sql)
            with engine.connect() as conn:
                res = conn.execute(q, {"d1": d_from, "d2": d_to})
                data = []
                for r in res:
                    data.append({
                        "status": r[0] or "Unknown",
                        "cnt": int(r[1] or 0),
                        "revenue": float(r[2]) if r[2] is not None else 0.0
                    })
                return {"status_breakdown": data}
        except Exception as e:
            print(f"[AnalyticsService] Error during status breakdown fetch: {e}")
        return {"status_breakdown": []}

    @classmethod
    def get_products(cls, d_from: str, d_to: str, limit: int = 25, segments: str = None) -> dict:
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)
            if cte:
                cte = cte + ", top_ids AS ("
            else:
                cte = "WITH top_ids AS ("
                
            sql = cte + """
                    SELECT product_id,
                           ROUND(SUM(sale_price)::numeric,2) AS revenue,
                           COUNT(*) AS units
                    FROM fact_orders
            """ + join_clause + """
                    WHERE order_date >= CAST(:d1 AS DATE) AND order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                      AND status NOT IN ('Cancelled','Returned')
                    GROUP BY product_id
                    ORDER BY revenue DESC
                    LIMIT :lim
                )
                SELECT dp.name AS product, dp.category, dp.brand, ti.revenue, ti.units
                FROM top_ids ti
                JOIN dim_products dp ON ti.product_id = dp.product_id
                ORDER BY ti.revenue DESC
            """
            q = text(sql)
            with engine.connect() as conn:
                res = conn.execute(q, {"d1": d_from, "d2": d_to, "lim": limit})
                data = []
                for r in res:
                    data.append({
                        "product": r[0] or "Unknown Product",
                        "category": r[1] or "Unknown Category",
                        "brand": r[2] or "Unknown Brand",
                        "revenue": float(r[3] or 0.0),
                        "units": int(r[4] or 0)
                    })
                return {"products": data}
        except Exception as e:
            print(f"[AnalyticsService] Error during products fetch: {e}")
        return {"products": []}

    @classmethod
    def get_categories(cls, d_from: str, d_to: str, segments: str = None) -> dict:
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)
            sql = (cte or "") + """
                SELECT dp.category,
                       ROUND(SUM(fo.sale_price)::numeric,2) AS revenue,
                       COUNT(*) AS orders,
                       ROUND(AVG(fo.sale_price)::numeric,2) AS avg_price
                FROM fact_orders fo
                JOIN dim_products dp ON fo.product_id = dp.product_id
            """ + join_clause + """
                WHERE fo.order_date >= CAST(:d1 AS DATE) AND fo.order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                  AND fo.status NOT IN ('Cancelled','Returned')
                GROUP BY dp.category ORDER BY revenue DESC
            """
            q = text(sql)
            with engine.connect() as conn:
                res = conn.execute(q, {"d1": d_from, "d2": d_to})
                data = []
                for r in res:
                    data.append({
                        "category": r[0] or "Unknown Category",
                        "revenue": float(r[1] or 0.0),
                        "orders": int(r[2] or 0),
                        "avg_price": float(r[3] or 0.0)
                    })
                return {"categories": data}
        except Exception as e:
            print(f"[AnalyticsService] Error during categories fetch: {e}")
        return {"categories": []}

    @classmethod
    def get_rfm_distribution(cls, d_from: str, d_to: str, segments: str = None) -> dict:
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)
            if cte:
                cte = cte + ", base AS ("
            else:
                cte = "WITH base AS ("
                
            sql = cte + """
                    SELECT customer_id,
                           COUNT(DISTINCT order_id)            AS frequency,
                           ROUND(SUM(sale_price)::numeric, 2)  AS monetary,
                           (CURRENT_DATE - MAX(order_date)::date) AS recency
                    FROM fact_orders
            """ + join_clause + """
                    WHERE order_date >= CAST(:d1 AS DATE)
                      AND order_date <  (CAST(:d2 AS DATE) + INTERVAL '1 day')
                      AND status NOT IN ('Cancelled', 'Returned')
                    GROUP BY customer_id

                ),
                ranked AS (
                    SELECT *,
                           NTILE(5) OVER (ORDER BY recency DESC)                 AS r_score,
                           NTILE(5) OVER (ORDER BY frequency ASC, recency DESC)  AS f_score,
                           NTILE(5) OVER (ORDER BY monetary ASC,  recency DESC)  AS m_score
                    FROM base
                ),
                segmented AS (
                    SELECT *,
                           (r_score + f_score + m_score) AS rfm_total,
                           CASE
                               WHEN (r_score + f_score + m_score) >= 13 THEN 'Champion'
                               WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal'
                               WHEN (r_score + f_score + m_score) >=  7 THEN 'Potential'
                               WHEN (r_score + f_score + m_score) >=  4 THEN 'At Risk'
                               ELSE 'Lost'
                           END AS segment_key,
                           (monetary / 50)::int * 50 AS monetary_bin
                    FROM ranked
                )
                SELECT segment_key,
                       frequency,
                       monetary_bin                    AS monetary,
                       ROUND(AVG(recency)::numeric, 1) AS recency,
                       COUNT(*)                        AS cnt
                FROM segmented
                GROUP BY segment_key, frequency, monetary_bin
                ORDER BY segment_key, frequency
            """

            EMOJI_MAP = {
                "Champion": "\U0001f3c6 Champion",
                "Loyal":    "\U0001f49a Loyal",
                "Potential":"\U0001f331 Potential",
                "At Risk":  "\u26a0\ufe0f At Risk",
                "Lost":     "\u274c Lost",
            }

            with engine.connect() as conn:
                res = conn.execute(text(sql), {"d1": d_from, "d2": d_to})
                rows = []
                for r in res:
                    rows.append({
                        "segment":   EMOJI_MAP.get(str(r[0]), str(r[0])),
                        "frequency": int(r[1]),
                        "monetary":  float(r[2]),
                        "recency":   float(r[3]),
                        "count":     int(r[4]),
                    })

            return {"rfm": rows}

        except Exception as e:
            print(f"[AnalyticsService] Database error during RFM fetch: {e}")
        return {"rfm": []}

    @classmethod
    def get_segment_categories(cls, d_from: str, d_to: str, segments: str = None) -> dict:
        try:
            engine = get_engine()
            cte, join_clause = cls._build_segment_cte(segments)
            if cte:
                cte = cte + ", customer_rfm AS ("
            else:
                cte = "WITH customer_rfm AS ("
                
            sql = cte + """
                    SELECT customer_id,
                           COUNT(DISTINCT order_id) AS frequency,
                           SUM(sale_price) AS monetary,
                           CURRENT_DATE - MAX(order_date)::date AS recency
                    FROM fact_orders
            """ + join_clause + """
                    WHERE order_date >= CAST(:d1 AS DATE) AND order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                      AND status NOT IN ('Cancelled','Returned')
                    GROUP BY customer_id

                ),
                scored_rfm AS (
                    SELECT customer_id,
                           NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
                           NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
                           NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
                    FROM customer_rfm
                ),
                segment_rfm AS (
                    SELECT customer_id,
                           (r_score + f_score + m_score) AS rfm_score
                    FROM scored_rfm
                ),
                customer_segments AS (
                    SELECT customer_id,
                           CASE 
                               WHEN rfm_score >= 13 THEN '🏆 Champion'
                               WHEN rfm_score >= 10 THEN '💚 Loyal'
                               WHEN rfm_score >= 7  THEN '🌱 Potential'
                               WHEN rfm_score >= 4  THEN '⚠️  At Risk'
                               ELSE '❌ Lost'
                           END AS segment
                    FROM segment_rfm
                ),
                order_categories AS (
                    SELECT fo.customer_id, dp.category
                    FROM fact_orders fo
                    JOIN dim_products dp ON fo.product_id = dp.product_id
                    WHERE fo.order_date >= CAST(:d1 AS DATE) AND fo.order_date < (CAST(:d2 AS DATE) + INTERVAL '1 day')
                      AND fo.status NOT IN ('Cancelled','Returned')
                ),
                segment_category_counts AS (
                    SELECT cs.segment, oc.category, COUNT(*) AS txn_count,
                           ROW_NUMBER() OVER (PARTITION BY cs.segment ORDER BY COUNT(*) DESC) as rn
                    FROM customer_segments cs
                    JOIN order_categories oc ON cs.customer_id = oc.customer_id
                    GROUP BY cs.segment, oc.category
                )
                SELECT segment, category
                FROM segment_category_counts
                WHERE rn = 1;
            """
            with engine.connect() as conn:
                res = conn.execute(text(sql), {"d1": d_from, "d2": d_to})
                mapping = {}
                for r in res:
                    if r[0] and r[1]:
                        mapping[str(r[0])] = str(r[1])
                return mapping
        except Exception as e:
            print(f"[AnalyticsService] Database error during segment categories fetch: {e}")
        return {
            "🏆 Champion": "Unknown",
            "💚 Loyal": "Unknown",
            "🌱 Potential": "Unknown",
            "⚠️  At Risk": "Unknown",
            "❌ Lost": "Unknown"
        }
