---
title: E-Commerce Customer Intelligence System V3
emoji: 🛍️
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---

# E-Commerce Customer Intelligence System V3 🛍️

> **Enterprise-Grade MLOps Pipeline** — Fully autonomous customer intelligence system featuring advanced AI Churn Prediction, Customer Lifetime Value (CLV), Product Recommendations, RAG AI Assistant (Text-to-SQL via Groq), drift monitoring, auto-retraining, and CI/CD hardening.

[![CI/CD](https://github.com/Rxseboy/ai-customer-intelligence-dashboard/actions/workflows/production_ci_cd.yml/badge.svg)](https://github.com/Rxseboy/ai-customer-intelligence-dashboard/actions)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![React](https://img.shields.io/badge/React-Vite%20%2B%20TypeScript-61DAFB)
![Airflow](https://img.shields.io/badge/Airflow-2.9-red)
![MLflow](https://img.shields.io/badge/MLflow-tracking-orange)
![Docker](https://img.shields.io/badge/Docker-compose-blue)
![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203-purple)

---

## 🏗️ System Architecture

```
BigQuery (thelook_ecommerce)
        │
        ▼
  ┌─────────────┐
  │ Airflow ETL │  ← @daily: Extract → Validate → Transform → Load
  └──────┬──────┘
         │ PostgreSQL Star Schema (Supabase)
         ▼
  ┌──────────────────────────┐
  │   Feature Store (v2.0)   │  ← rfm / time_series / user features
  └──────────┬───────────────┘
             │
             ▼
  ┌──────────────────────────┐        ┌────────────────────┐
  │  ML Pipeline (run_all)   │───────▶│  MLflow Tracking   │
  │ Churn·Segment·CLV·Recsys │        │  (localhost:5000)  │
  └──────────┬───────────────┘        └────────────────────┘
             │
             ▼
  ┌────────────────────────────┐
  │   Drift Monitor            │  ← Z-score detection
  │   (drift_monitor.py)       │
  └────────────┬───────────────┘
               │ drift detected?
               ▼
  ┌────────────────────────────┐
  │  Auto Retrain DAG          │  ← Airflow: ecommerce_auto_retrain
  └────────────────────────────┘
             │
             ▼
  ┌────────────────────────────┐
  │   FastAPI Backend          │  ← http://localhost:10000
  │   (src/back_end/api/)      │
  └────────────┬───────────────┘
               │ REST API
               ▼
  ┌────────────────────────────┐
  │   React Dashboard (Vite)   │  ← http://localhost:5173
  │   (src/frontend/)          │
  └────────────────────────────┘
```

---

## 📁 Project Structure

```
.
├── dags/                          # Airflow DAGs (production pipelines)
│   ├── ecommerce_etl.py           # Daily ETL: BigQuery → PostgreSQL
│   └── ecommerce_retrain.py       # Auto-retrain on drift signal
├── data/
│   ├── processed/                 # Pre-computed RFM + scores (CSV)
│   └── baseline_stats.json        # Drift monitoring baseline
├── models/                        # Trained ML model artifacts (.pkl)
├── notebooks/
│   └── cek_connection.ipynb       # DB connection helper
├── reports/figures/               # Auto-generated charts
├── scripts/
│   ├── init_airflow.sh            # Airflow init script (Docker)
│   ├── setup_db.py                # Database schema setup
│   └── start_all.bat              # Windows one-click dev startup
├── src/
│   ├── back_end/
│   │   ├── api/
│   │   │   ├── main.py            # FastAPI app (1000+ lines → delegated)
│   │   │   ├── dependencies.py    # API Key auth
│   │   │   ├── schemas/           # Pydantic contracts
│   │   │   ├── services/          # Decoupled business logic
│   │   │   │   ├── analytics_service.py # Core SQL aggregations
│   │   │   │   └── model_cache.py # Thread-safe ML model singleton loader
│   │   │   └── routers/           # Modular FastAPI routing
│   │   │       ├── analytics.py   # Global metrics endpoints
│   │   │       ├── predictions.py # ML endpoints
│   │   │       ├── rag.py         # AI Insights endpoints
│   │   │       ├── monitoring.py  # Drift endpoints
│   │   │       └── health.py      # Health check
│   │   ├── ml/
│   │   │   ├── churn.py           # XGBoost churn model
│   │   │   ├── clv.py             # BG/NBD + Gamma-Gamma CLV
│   │   │   ├── data_loader.py     # SQLAlchemy DB connectors
│   │   │   ├── features/          # Feature Store package
│   │   │   │   ├── rfm_features.py
│   │   │   │   ├── user_features.py
│   │   │   │   ├── time_series_features.py
│   │   │   │   └── feature_registry.py
│   │   │   ├── forecasting_anomaly.py
│   │   │   ├── monitoring/
│   │   │   │   └── drift_monitor.py
│   │   │   ├── rag.py             # LangChain + Groq Text-to-SQL
│   │   │   ├── rag_eval.py        # Automated RAG evaluation
│   │   │   ├── recommendation.py  # Implicit ALS collaborative filtering
│   │   │   └── segmentation.py    # KMeans RFM segmentation
│   │   ├── config/config.py
│   │   └── pipelines/
│   │       └── run_all.py         # Local dev ML pipeline runner
│   └── frontend/                  # React + Vite + TypeScript dashboard
│       ├── src/
│       │   ├── components/
│       │   │   └── dashboard/tabs/
│       │   │       ├── revenue-overview.tsx
│       │   │       ├── customer-rfm.tsx
│       │   │       ├── churn-tab.tsx
│       │   │       ├── product-analytics.tsx
│       │   │       ├── ai-analyst.tsx
│       │   │       ├── ai-clv-tab.tsx
│       │   │       └── recommendation-tab.tsx
│       │   └── lib/api.ts         # Typed API client
│       ├── package.json
│       └── vite.config.ts
├── docker-compose.yml             # Airflow + FastAPI + MLflow
├── Dockerfile
├── requirements.txt
└── run_all_tests.py               # Test runner
```

---

## 🚀 Quick Start — Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or Supabase account)
- Docker Desktop (for Airflow, optional)

### 1. Clone & Setup Backend

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `DATABASE_URL_READONLY` | Read-only connection (optional) | Same as above or separate |
| `GROQ_API_KEY` | Groq API key for RAG AI Assistant | `gsk_...` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to BigQuery service account JSON | `./key.json` |
| `MLFLOW_TRACKING_URI` | MLflow server URI | `http://localhost:5000` |
| `API_KEY` | API authentication key | `your-secure-api-key-here` |

### 3. Start the FastAPI Backend

```bash
# Activate venv first
uvicorn src.back_end.api.main:app --reload --host 0.0.0.0 --port 10000
```

API docs available at → **http://localhost:10000/docs**

### 4. Start the React Frontend

```bash
cd src/frontend
npm install
npm run dev
```

Dashboard available at → **http://localhost:5173**

> ⚠️ The frontend reads `VITE_API_BASE_URL` from `src/frontend/.env`. Default: `http://localhost:10000`

### 5. (Optional) Run ML Pipeline Locally

```bash
# Train all models and compute customer scores
python src/back_end/pipelines/run_all.py
```

---

## 🐳 Docker Compose — Full Stack (Airflow + API + MLflow)

```bash
# Step 1: Initialize Airflow database (run ONCE)
docker compose up airflow-init

# Step 2: Start all services
docker compose up -d
```

| Service | URL | Purpose |
|---|---|---|
| Airflow WebUI | http://localhost:8080 | ETL + Retrain DAG management |
| FastAPI | http://localhost:10000 | ML inference + Analytics API |
| MLflow | http://localhost:5000 | Experiment tracking |

> **React Dashboard** is **not** part of docker-compose. Run it separately: `cd src/frontend && npm run dev`

**Docker Credentials:** `admin` / `admin`

---

## 🤖 ML Capabilities

| Feature | Model | Status |
|---|---|---|
| Churn Prediction | XGBoost + LogReg baseline | ✅ Active |
| Customer Segmentation | RFM KMeans (5 clusters) | ✅ Active |
| Customer Lifetime Value | BG/NBD + Gamma-Gamma | ✅ Active |
| Product Recommendations | Implicit ALS | ✅ Active |
| Revenue Forecasting | Prophet | ✅ Active |
| Anomaly Detection | IsolationForest | ✅ Active |
| AI Text-to-SQL | Groq Llama 3.3 70B (RAG) | ✅ Active |
| Drift Detection | Z-score + Evidently | ✅ Active |

---

## 📡 API Endpoints

```
GET  /health                        → System health (model, data, MLflow)
POST /predict/churn                 → Churn probability for a customer
POST /predict/segment               → RFM segment assignment
POST /predict/clv                   → Customer Lifetime Value
GET  /predict/recommendations       → ALS product recommendations
GET  /customers/top                 → Top N customers by revenue
GET  /insights                      → High-level KPIs
GET  /segments/summary              → Segment distribution
GET  /api/insights/kpis             → Date-filtered KPIs
GET  /api/insights/trend            → Revenue trend (weekly/monthly)
GET  /api/insights/status           → Order status breakdown
GET  /api/insights/products         → Top products by revenue
GET  /api/insights/categories       → Category performance
GET  /api/insights/rfm              → RFM scatter data
POST /insights/ask                  → RAG AI natural language query
GET  /insights/tables               → Available DB tables for RAG
POST /insights/evaluate             → Auto-evaluate RAG quality
GET  /monitoring/drift              → Drift status
POST /monitoring/drift/check        → Run drift check now
```

All write/predict endpoints require: `X-API-Key: <API_KEY>` header.

---

## 🔁 MLOps Pipeline — Airflow DAGs

### `ecommerce_etl_pipeline` (runs `@daily`)
```
extract_data → transform_data → load_data
```
Extracts from Google BigQuery thelook_ecommerce, cleans and star-schemas the data, loads to Supabase PostgreSQL.

### `ecommerce_auto_retrain` (runs `@hourly`)
```
check_drift_signal → run_retrain → clear_retrain_signal → update_drift_baseline
```
Triggered when `DriftMonitor` writes `data/retrain_signal.flag`. Retrains all ML models and updates the baseline.

---

## 🧪 Testing

```bash
# Run full test suite
python run_all_tests.py

# Or with pytest directly
pytest tests/ -v
```

---

## 🔐 Security Notes

- All ML prediction endpoints are protected by `X-API-Key` authentication
- RAG Text-to-SQL has a multi-layer SQL safety validator (blocks DROP/DELETE/INSERT/UPDATE)
- CORS configured to allow all origins by default — restrict `allow_origins` in `main.py` for production
- API key should be rotated via environment variable in production

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: src.back_end` | Run from project root, ensure venv is activated |
| Frontend can't reach API | Check `VITE_API_BASE_URL` in `src/frontend/.env` |
| Churn model not found | Run `python src/back_end/pipelines/run_all.py` first |
| Airflow shows no DAGs | Ensure `dags/` volume is mounted in docker-compose |
| RAG returns `503` | Set `GROQ_API_KEY` in `.env` and install `langchain-groq` |
| DB connection error | Verify `DATABASE_URL` in `.env`; check Supabase IP allow-list |

---

## 👤 Author

**Rizqi Fajar**  
rizqyfajar99@gmail.com  
[GitHub: Rxseboy](https://github.com/Rxseboy)
