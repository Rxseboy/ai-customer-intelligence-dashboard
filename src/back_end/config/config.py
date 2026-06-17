"""
config.py
=========
Konfigurasi terpusat untuk ETL Pipeline.
Semua nilai dibaca otomatis dari file .env
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env dari folder yang sama dengan file ini
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


@dataclass
class BigQueryConfig:
    """Konfigurasi koneksi ke BigQuery."""
    credentials_path: str = field(default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "key.json"))
    project_dataset: str  = "bigquery-public-data.thelook_ecommerce"


@dataclass
class PostgresConfig:
    """Konfigurasi koneksi ke PostgreSQL."""
    user: str     = field(default_factory=lambda: os.getenv("DB_USER",     "postgres"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    host: str     = field(default_factory=lambda: os.getenv("DB_HOST",     "localhost"))
    port: str     = field(default_factory=lambda: os.getenv("DB_PORT",     "5432"))
    dbname: str   = field(default_factory=lambda: os.getenv("DB_NAME",     "ecommerce_dw"))

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


# Instance siap pakai
bq_config = BigQueryConfig()
pg_config = PostgresConfig()


if __name__ == "__main__":
    print("=== Konfigurasi aktif ===")
    print(f"BigQuery credentials : {bq_config.credentials_path}")
    print(f"BigQuery dataset     : {bq_config.project_dataset}")
    print(f"PostgreSQL host      : {pg_config.host}:{pg_config.port}")
    print(f"PostgreSQL database  : {pg_config.dbname}")
    print(f"PostgreSQL user      : {pg_config.user}")
    print(f"PostgreSQL password  : {'*' * len(pg_config.password)}")
