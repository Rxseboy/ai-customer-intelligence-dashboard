"""
pipeline.py
===========
Orchestrator utama ETL Pipeline.

Cara menjalankan:
    python pipeline.py

Alur:
    BigQuery → Extract → Transform (Clean + Star Schema) → Load → PostgreSQL
"""

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Masukkan root directory ke sys.path agar module 'src' terbaca
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env PERTAMA sebelum import modul lain (dari root project)
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

from src.back_end.etl.extract import extract_all_tables
from src.back_end.etl.transform import run_transform
from src.back_end.etl.load import connect_db, load_all, verify_load

# ==============================================================================
# KONFIGURASI LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


# ==============================================================================
# MAIN PIPELINE
# ==============================================================================

def run_pipeline() -> None:
    """
    Menjalankan full ETL pipeline:
      1. Extract  → Ambil SEMUA data dari BigQuery
      2. Transform → Bersihkan + bentuk star schema
      3. Load      → Simpan ke PostgreSQL
    """
    start_time = time.time()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("=" * 60)
    logger.info(f"  CUSTOMER INTELLIGENCE ETL PIPELINE")
    logger.info(f"  Run ID  : {run_id}")
    logger.info(f"  Dataset : bigquery-public-data.thelook_ecommerce (FULL)")
    logger.info(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # STEP 1: EXTRACT
    # ------------------------------------------------------------------
    t0 = time.time()
    raw_data = extract_all_tables()
    logger.info(f"\n⏱️  Extract selesai dalam {time.time() - t0:.1f} detik\n")

    # ------------------------------------------------------------------
    # STEP 2: TRANSFORM
    # ------------------------------------------------------------------
    t1 = time.time()
    star_schema = run_transform(raw_data)
    logger.info(f"\n⏱️  Transform selesai dalam {time.time() - t1:.1f} detik\n")

    # ------------------------------------------------------------------
    # STEP 3: LOAD
    # ------------------------------------------------------------------
    t2 = time.time()
    engine = connect_db()
    load_all(star_schema, engine)
    logger.info(f"\n⏱️  Load selesai dalam {time.time() - t2:.1f} detik\n")

    # ------------------------------------------------------------------
    # VERIFIKASI
    # ------------------------------------------------------------------
    verify_load(engine)

    # ------------------------------------------------------------------
    # RINGKASAN
    # ------------------------------------------------------------------
    elapsed = time.time() - start_time
    logger.info("\n" + "=" * 60)
    logger.info(f"  ✅ PIPELINE SELESAI!")
    logger.info(f"  Total waktu : {elapsed:.1f} detik ({elapsed/60:.1f} menit)")
    logger.info(f"  Log disimpan: pipeline.log")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()
