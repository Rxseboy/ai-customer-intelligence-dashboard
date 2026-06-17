@echo off
echo ==========================================
echo   Running System Tests...
echo ==========================================
venv\Scripts\python.exe tests\test_system.py > test_results.log 2>&1
echo.
echo ==========================================
echo   Running API Tests...
echo ==========================================
venv\Scripts\python.exe tests\test_api.py >> test_results.log 2>&1
echo Done. See test_results.log for output.
type test_results.log
