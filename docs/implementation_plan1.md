# Step 2: Airflow Orchestration — Implementation Plan

## Latar Belakang

Pipeline ETL sudah berjalan via `python pipeline.py`. Step ini mengubahnya menjadi
Airflow DAG yang berjalan otomatis terjadwal.

## ⚠️ User Review Required

> [!IMPORTANT]
> **Airflow TIDAK berjalan native di Windows.**
> Airflow hanya mendukung Linux/macOS secara resmi. Di Windows, ada 2 pilihan:
>
> **Pilihan A — WSL2 (Rekomendasi)**
> - Install Ubuntu via Microsoft Store
> - Jalankan Airflow di dalam WSL2
> - Bisa akses project dari `/mnt/c/Users/rizqy/...`
>
> **Pilihan B — Docker Desktop (Paling Production-Like)**
> - Install Docker Desktop
> - Jalankan Airflow via `docker compose`
>
> Saya akan buat setup untuk **WSL2** karena lebih ringan dan mudah.

> [!WARNING]
> **Versi Airflow**: Airflow 3.1.3 di request **tidak tersedia**.
> Versi latest stable saat ini adalah **Airflow 3.1.8**.
> Kita gunakan 3.1.8 dengan Python 3.10.

> [!CAUTION]
> **Pickle tidak aman untuk production.**
> Kita gunakan **Parquet** untuk pertukaran data antar task (seperti disebutkan di Best Practice).

---

## Proposed Changes

### Struktur Folder Baru

```
Costumer Intelligence System/
│
├── etl/                        ← [NEW] Package ETL (pindah dari root)
│   ├── __init__.py
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── dags/                       ← [NEW] Airflow DAG folder
│   └── ecommerce_etl.py
│
├── data/                       ← [NEW] Temp Parquet files antar task
│   ├── raw/                    ← Output extract task
│   └── processed/              ← Output transform task
│
├── config.py                   ← [KEEP] Konfigurasi .env
├── setup_db.py                 ← [KEEP]
├── verify_pipeline.py          ← [KEEP]
├── pipeline.py                 ← [KEEP] Direct run (backup)
├── .env                        ← [KEEP]
└── requirements.txt            ← [MODIFY] Tambah airflow
```

---

### [NEW] `etl/` Package

#### [NEW] etl/__init__.py
Package marker.

#### [NEW] etl/extract.py
Salin dari `extract.py` root, sesuaikan import path.

#### [NEW] etl/transform.py
Salin dari `transform.py` root, sesuaikan import path.

#### [NEW] etl/load.py
Salin dari `load.py` root, sesuaikan import path.

---

### [NEW] `dags/ecommerce_etl.py`
Airflow DAG dengan 3 task:
- `extract_data` → extract semua tabel → simpan ke `data/raw/*.parquet`
- `transform_data` → baca parquet → clean + star schema → simpan ke `data/processed/*.parquet`
- `load_data` → baca parquet → load ke PostgreSQL

DAG schedule: `@daily` (jalan setiap hari otomatis)

---

### [MODIFY] `requirements.txt`
Tambah `apache-airflow==3.1.8` dan `pyarrow` (sudah ada).

---

## Setup WSL2 (Langkah Manual)

Karena Airflow harus dijalankan di WSL2, berikut langkah yang perlu dilakukan **manual** oleh user:

```bash
# Di WSL2 (Ubuntu)
cd /mnt/c/Users/rizqy/Desktop/Github-Repository-Management/"Costumer Intelligence System"

python3 -m venv airflow_venv
source airflow_venv/bin/activate

AIRFLOW_VERSION=3.1.8
PYTHON_VERSION=3.10

pip install "apache-airflow==${AIRFLOW_VERSION}" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install -r requirements.txt

export AIRFLOW_HOME=$(pwd)
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/key.json

airflow standalone
```

---

## Open Questions

> [!IMPORTANT]
> **Apakah kamu sudah punya WSL2 / Docker Desktop di Windows kamu?**
>
> - Jawab **"WSL2"** → Saya siapkan semua file + instruksi WSL2
> - Jawab **"Docker"** → Saya buatkan `docker-compose.yml` untuk Airflow
> - Jawab **"Belum ada"** → Saya bantu install WSL2 dulu
>
> Tanpa salah satu dari ini, Airflow **tidak bisa jalan di Windows**.

---

## Verification Plan

### Automated
- `airflow dags list` → DAG terdaftar
- `airflow dags test ecommerce_etl_pipeline` → Test tanpa scheduler

### Manual
1. Buka `http://localhost:8080`
2. Toggle DAG ON
3. Klik ▶️ Run
4. Cek semua task hijau (success)
5. Jalankan `python verify_pipeline.py` untuk cek data di PostgreSQL
