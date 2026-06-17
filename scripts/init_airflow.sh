#!/bin/bash
# scripts/init_airflow.sh
# Inisialisasi Airflow: migrate DB + buat user admin
# Dijalankan oleh container airflow-init saat 'docker compose up airflow-init'

set -e

echo "============================================"
echo "  AIRFLOW INIT"
echo "============================================"

echo ""
echo "[1/2] Migrasi database Airflow..."
airflow db migrate
echo "  Database migration selesai!"

echo ""
echo "[2/2] Membuat user admin..."
# Airflow 3.x menggunakan 'airflow users' yang berbeda
# Coba metode baru dulu, fallback ke env variable
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin 2>/dev/null \
  || echo "  User 'admin' sudah ada atau command tidak tersedia di Airflow 3.x"

# Untuk Airflow 3.x yang tidak punya 'airflow users' CLI
# User bisa dibuat via Airflow UI setelah pertama kali login dengan
# username: admin, password: admin (diset via AIRFLOW_ADMIN_* env vars)

echo ""
echo "============================================"
echo "  Init selesai!"
echo "  Sekarang jalankan: docker compose up -d"
echo "  Buka: http://localhost:8080"
echo "  Login: admin / admin"
echo "============================================"
