@echo off
REM ============================================================
REM  start_all.bat — Jalankan semua services Customer Intelligence System
REM  Usage: start_all.bat [streamlit_port]
REM ============================================================

SET PORT=%1
IF "%PORT%"=="" SET PORT=8501

echo.
echo ============================================================
echo  Customer Intelligence System — Startup
echo ============================================================
echo.

REM 1. Activate venv
call .\venv\Scripts\activate.bat

REM 2. Cek PostgreSQL
echo [1/3] Checking PostgreSQL...
python -c "from models.data_loader import get_engine; from sqlalchemy import text; e=get_engine(); e.connect().execute(text('SELECT 1')); print('  PostgreSQL: OK')" 2>nul
IF ERRORLEVEL 1 (
    echo   [ERROR] PostgreSQL tidak berjalan!
    echo   Jalankan PostgreSQL terlebih dahulu, lalu coba lagi.
    echo   Atau jalankan: net start postgresql-x64-14
    pause
    exit /b 1
)

REM 3. Cek apakah ML models sudah ada
IF NOT EXIST "outputs\customer_scores.csv" (
    echo [2/3] ML models belum ada - menjalankan pipeline...
    python models\run_all.py --threshold 90
) ELSE (
    echo [2/3] ML models sudah ada di outputs\ - skip training
    echo   Untuk retrain: python models\run_all.py --threshold 90
)

REM 4. Start FastAPI (background)
echo [3/3] Starting FastAPI di http://localhost:8000 ...
start "FastAPI" cmd /k "call .\venv\Scripts\activate.bat && uvicorn api.main:app --host 0.0.0.0 --port 8000"

REM 5. Start Streamlit (foreground)
echo.
echo Starting Streamlit di http://localhost:%PORT% ...
echo Press Ctrl+C to stop.
echo.
streamlit run dashboard.py --server.port %PORT%
