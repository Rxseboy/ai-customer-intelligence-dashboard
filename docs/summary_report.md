# 📊 Laporan Proyek: Customer Intelligence System
**Tanggal Laporan:** 5 April 2026  
**Proyek:** thelook eCommerce — Customer Intelligence Pipeline  
**Author:** Rizqy  
**Tech Stack:** Python · BigQuery · PostgreSQL · Apache Airflow · Streamlit · Scikit-learn · XGBoost

---

## 🎯 Ringkasan Eksekutif

Proyek ini berhasil membangun sebuah **sistem intelijen pelanggan end-to-end** yang mengotomatisasi seluruh alur dari pengambilan data mentah di Google BigQuery, pembersihan dan transformasi ke skema data warehouse (Star Schema), pemodelan machine learning, hingga visualisasi interaktif melalui dashboard Streamlit. Sistem ini dirancang untuk membantu tim bisnis memahami perilaku pelanggan, mendeteksi risiko churn, dan mengambil keputusan berbasis data.

---

## 🏗️ Arsitektur Sistem

```
Google BigQuery (Source)
        │
        ▼
   [ETL Pipeline]
   Extract → Transform → Load
        │
        ▼
PostgreSQL (Data Warehouse)
  ┌─────────────────────┐
  │     Star Schema     │
  │  ┌───────────────┐  │
  │  │  fact_orders  │  │
  │  └──────┬────────┘  │
  │  dim_customers      │
  │  dim_products       │
  │  dim_date           │
  └─────────────────────┘
        │
        ▼
  [ML Pipeline]
  RFM → KMeans → XGBoost
        │
        ▼
  Streamlit Dashboard
```

Seluruh pipeline dijadwalkan otomatis setiap hari menggunakan **Apache Airflow DAG** (`ecommerce_etl_pipeline`), sehingga data selalu up-to-date tanpa intervensi manual.

---

## 📁 Struktur Modul & Penjelasan

| Modul / File | Fungsi |
|---|---|
| `etl/extract.py` | Mengambil data dari Google BigQuery (orders, order_items, users, products) |
| `etl/transform.py` | Membersihkan data + membentuk Star Schema (4 tabel) |
| `etl/load.py` | Memuat Star Schema ke PostgreSQL |
| `dags/ecommerce_etl.py` | Airflow DAG — orkestrasi ETL harian otomatis |
| `models/features.py` | Feature engineering: kalkulasi RFM + churn label |
| `models/segmentation.py` | Segmentasi pelanggan dengan KMeans (4 cluster) |
| `models/churn.py` | Prediksi churn dengan XGBoost + evaluasi model |
| `models/insights.py` | Kalkulasi business insights: Pareto, churn risk, segment stats |
| `models/run_all.py` | Pipeline ML end-to-end (Load → RFM → Segmentasi → Churn → Insights) |
| `dashboard.py` | Streamlit dashboard interaktif dengan 4 tab analitik |
| `config.py` | Konfigurasi terpusat (DB, BigQuery, paths) |

---

## 🔄 Step 1 — ETL Pipeline (Extract → Transform → Load)

### Sumber Data
Dataset yang digunakan adalah **`bigquery-public-data.thelook_ecommerce`** — dataset publik Google BigQuery yang mensimulasikan toko e-commerce dengan data orders, produk, dan pelanggan yang realistis.

| Tabel Sumber (BigQuery) | Digunakan Untuk |
|---|---|
| `orders` | Status & tanggal order |
| `order_items` | Detail item per order (harga, produk) |
| `users` | Data demografi pelanggan |
| `products` | Katalog produk (kategori, brand, harga) |

### Proses Pembersihan Data
Setiap tabel dibersihkan secara terpisah dengan aturan khusus:

| Tabel | Pembersihan yang Dilakukan |
|---|---|
| `orders` | Hapus duplikat, parsing tanggal, **hapus order berstatus "Cancelled"**, drop row NULL critical |
| `order_items` | Hapus duplikat, validasi harga ≥ 0, drop NULL pada kolom kunci |
| `users` | Hapus duplikat, normalisasi gender (Title Case), normalisasi country (UPPER), drop email NULL |
| `products` | Hapus duplikat, validasi retail_price ≥ 0, normalisasi kategori & brand |

### Star Schema yang Dihasilkan

```
                    ┌──────────────────┐
                    │   dim_customers  │
                    │  customer_id  PK │
                    └────────┬─────────┘
                             │
┌──────────────┐    ┌────────▼─────────┐    ┌──────────────┐
│  dim_date    │    │   fact_orders    │    │ dim_products │
│  date_id  PK ├────┤  fact_id      PK ├────┤ product_id PK│
└──────────────┘    │  order_id        │    └──────────────┘
                    │  customer_id  FK │
                    │  product_id   FK │
                    │  date_id      FK │
                    │  sale_price      │
                    │  status          │
                    │  margin          │
                    └──────────────────┘
```

**Keunggulan Star Schema:**
- Query analytics jauh lebih cepat dibanding flat table
- Mudah di-join untuk berbagai sudut analisis (waktu, produk, pelanggan)
- Kolom `margin` dihitung otomatis (`sale_price - cost`)
- `dim_date` dibangun otomatis dari rentang tanggal transaksi (termasuk informasi hari, minggu, kuartal, weekend/weekday)

### Otomasi dengan Apache Airflow
DAG `ecommerce_etl_pipeline` berjalan **setiap hari** dengan 3 task terurut:

```
extract_data → transform_data → load_data
```

- **Toleransi kegagalan:** Retry otomatis 2x dengan interval 5 menit
- **Inter-task storage:** File Parquet (format binary columnar yang efisien)
- **Tidak ada XCom overhead** — data antar task disimpan dalam file system

---

## 🤖 Step 2 — Machine Learning Pipeline

### A. Feature Engineering — Analisis RFM

RFM adalah metode analitik standar industri untuk mengukur nilai pelanggan berdasarkan tiga dimensi:

| Metrik | Definisi | Cara Hitung |
|---|---|---|
| **Recency (R)** | Seberapa baru pelanggan berbelanja | `(snapshot_date - tanggal_order_terakhir).days` |
| **Frequency (F)** | Seberapa sering pelanggan berbelanja | Jumlah order unik |
| **Monetary (M)** | Total nilai belanja pelanggan | Jumlah `sale_price` |

Fitur tambahan yang dihasilkan:
- `avg_order_value` = monetary / frequency
- `unique_categories` — jumlah kategori produk berbeda yang pernah dibeli
- `avg_unit_price` — rata-rata harga per item
- `total_items` — total item yang pernah dibeli
- `churn` — label biner: 1 jika recency > 30 hari (tidak beli dalam 30 hari terakhir)

### B. Segmentasi Pelanggan — KMeans Clustering

**Algoritma:** KMeans dengan `n_clusters=4`, dioptimasi dengan Elbow Method + Silhouette Score.

**4 Segmen yang Dihasilkan:**

| Segmen | Karakteristik | Strategi Bisnis |
|---|---|---|
| 🏆 **Champions** | Recency rendah, Frequency tinggi, Monetary tinggi | Pertahankan dengan VIP benefits & early access |
| 💚 **Loyal** | Sering beli, spending cukup besar | Upsell produk premium, loyalty program |
| 🌱 **Potential** | Baru mulai, potensi berkembang | Edukasi produk, free shipping threshold |
| ⚠️ **At Risk** | Dulu aktif, tapi sudah lama tidak beli | Kampanye re-engagement dengan diskon personal |

**Kualitas Model:**
- Silhouette Score digunakan untuk validasi kualitas clustering
- Label cluster ditentukan secara **dinamis** berdasarkan centroid (bukan hardcoded)
- Formula scoring: `monetary - recency × 0.3 + frequency × 2`

### C. Prediksi Churn — XGBoost Classifier

**Algoritma:** XGBoost dengan hyperparameter yang dikalibrasi untuk data imbalanced.

**Konfigurasi Model:**
```
n_estimators     = 200
max_depth        = 4
learning_rate    = 0.05
subsample        = 0.8
colsample_bytree = 0.8
scale_pos_weight = (jumlah_non_churn / jumlah_churn)  ← mengatasi imbalance
```

**Fitur Input Model:**
| Fitur | Deskripsi |
|---|---|
| `recency` | Hari sejak pembelian terakhir |
| `frequency` | Jumlah order |
| `monetary` | Total pengeluaran |
| `avg_order_value` | Rata-rata nilai per order |

**Output Model:**
- `churn_probability` — probabilitas churn (0.0 – 1.0) per pelanggan
- `risk_level` — klasifikasi risiko:
  - 🟢 **Low** (prob < 0.3)
  - 🟡 **Medium** (prob 0.3 – 0.6)  
  - 🔴 **High** (prob > 0.6)

**Evaluasi Model:**
- Classification Report (precision, recall, F1-score)
- ROC-AUC Score
- 5-Fold Stratified Cross-Validation

### D. Business Insights yang Dihasilkan

| Insight | Formulasi |
|---|---|
| **Pareto Effect** | Top 20% pelanggan → X% revenue (Prinsip 80/20) |
| **Churn Rate** | % pelanggan dengan recency > 30 hari |
| **Revenue at Risk** | Total revenue dari pelanggan berisiko churn |
| **Segment Statistics** | Rata-rata RFM + total revenue per segmen |

---

## 📈 Output Files yang Dihasilkan

Semua output disimpan di folder `outputs/`:

| File | Isi |
|---|---|
| `rfm_data.csv` | Tabel RFM per pelanggan (recency, frequency, monetary + features) |
| `customer_scores.csv` | RFM + segmen KMeans + churn probability + risk level |
| `segmentation.png` | Scatter plot Frequency vs Monetary per segmen |
| `optimal_k.png` | Elbow curve + Silhouette Score (pemilihan jumlah cluster) |
| `confusion_matrix.png` | Confusion matrix model XGBoost |
| `roc_curve.png` | ROC-AUC Curve churn model |
| `feature_importance.png` | Feature importance XGBoost |
| `pareto.png` | Grafik Pareto konsentrasi revenue pelanggan |

---

## 📊 Step 3 — Interactive Dashboard (Streamlit)

Dashboard diakses melalui `streamlit run dashboard.py` dan menampilkan **4 tab analitik**:

### Tab 1: 📈 Revenue Overview
- **KPI Cards:** Total Revenue, Total Orders, Average Order Value, Unique Customers
- **Dual-axis chart:** Revenue (bar) + Orders (line) per periode (Monthly/Weekly)
- **Pie chart:** Distribusi Revenue by Order Status
- **Summary Table:** Rekap pendapatan per periode

### Tab 2: 👥 Customer RFM
- **Bar Chart:** Jumlah pelanggan per segmen RFM
- **Pie Chart:** Kontribusi revenue per segmen
- **RFM Scatter Plot:** Frequency vs Monetary, warna per segmen, ukuran = recency
- **Pareto Curve:** Visualisasi efek 80/20 interaktif
- **Top 10 Customers:** Tabel pelanggan dengan revenue tertinggi

### Tab 3: 📦 Products
- **Top 20 Products:** Bar chart horizontal by revenue
- **Category Treemap:** Ukuran = total revenue, warna = avg price
- **Brand Performance:** Bar chart top 15 brand

### Tab 4: 💡 Insights
- **Key Business Insights:** Pareto Effect, Churn Risk Alert, Champion Contribution, Behavioral Pattern
- **Strategic Recommendations:** Retain Champions, Re-engage At-Risk, Upsell Potentials, Predict Churn (ML)

**Fitur Dashboard:**
- Filter **Date Range** dinamis (from – to)
- Granularitas trend: **Monthly / Weekly**
- Filter **segmen RFM** (multi-select)
- Data di-cache 1 jam (`@st.cache_data(ttl=3600)`) untuk performa optimal
- Dark mode design dengan color palette yang konsisten

---

## 🐳 Deployment & Infrastruktur

Proyek siap di-deploy menggunakan **Docker Compose** dengan container:

| Service | Image | Port |
|---|---|---|
| Apache Airflow | `apache/airflow` | 8080 |
| PostgreSQL | `postgres:15` | 5432 |
| Streamlit Dashboard | Custom (Python 3.11) | 8501 |

```yaml
# docker-compose.yml — tiga service utama:
airflow → orkestrasi ETL harian
postgres → data warehouse Star Schema
streamlit → dashboard analitik
```

---

## ✅ Pencapaian & Status

| Komponen | Status | Keterangan |
|---|---|---|
| ETL Pipeline (Extract) | ✅ Selesai | BigQuery → Parquet |
| ETL Pipeline (Transform) | ✅ Selesai | Cleaning + Star Schema |
| ETL Pipeline (Load) | ✅ Selesai | PostgreSQL dengan upsert |
| Airflow DAG | ✅ Selesai | Jadwal harian, retry logic |
| Feature Engineering (RFM) | ✅ Selesai | + Product features |
| KMeans Segmentation | ✅ Selesai | 4 cluster dinamis |
| XGBoost Churn Prediction | ✅ Selesai | + Cross-validation |
| Business Insights | ✅ Selesai | Pareto, Churn Risk, Segment Stats |
| Streamlit Dashboard | ✅ Selesai | 4 tab, real-time dari PostgreSQL |
| Docker Compose | ✅ Selesai | Siap deploy multi-container |

---

## 🚀 Rekomendasi Next Steps

1. **Model Retraining Otomatis** — Tambahkan Airflow DAG kedua khusus untuk retrain model ML setiap minggu dengan data terbaru
2. **Alert System** — Notifikasi email/Slack ketika churn rate melampaui threshold tertentu
3. **A/B Testing Framework** — Tracking efektivitas campaign re-engagement berdasarkan segmen
4. **Feature Store** — Centralize fitur RFM agar bisa digunakan oleh multiple model
5. **Model Monitoring** — Pantau drift pada distribusi data input + performa model di production
6. **API Endpoint** — Ekspos prediksi churn sebagai REST API untuk integrasi dengan CRM

---

## 📌 Cara Menjalankan Pipeline Lengkap

```powershell
# 1. Aktifkan virtual environment
venv\Scripts\activate

# 2. Setup database (jalankan SEKALI)
python setup_db.py

# 3. Jalankan ETL pipeline
python pipeline.py

# 4. Jalankan ML pipeline
python models\run_all.py

# 5. Jalankan dashboard
streamlit run dashboard.py

# ATAU: jalankan semua via Docker
docker-compose up -d
```

---

*Laporan ini dihasilkan otomatis berdasarkan analisis kode sumber proyek Customer Intelligence System.*  
*Seluruh komponen telah diimplementasikan dan siap untuk dioperasikan pada lingkungan produksi.*
