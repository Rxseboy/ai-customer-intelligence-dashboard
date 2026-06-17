"""
start.py — Customer Intelligence System Launcher
Menjalankan FastAPI backend + React frontend secara bersamaan dengan satu perintah.

Cara pakai:
    python start.py
    python start.py --backend-only
    python start.py --frontend-only

Tekan Ctrl+C untuk menghentikan semua proses.
"""
import subprocess
import sys
import os
import time
import argparse
import signal
import platform

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "src", "frontend")

BACKEND_CMD = [
    sys.executable, "-m", "uvicorn",
    "src.back_end.api.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
]

# Detect package manager for frontend
def get_frontend_cmd():
    import platform
    is_win = platform.system() == "Windows"
    for pm in ["bun", "pnpm", "npm"]:
        cmd_name = f"{pm}.cmd" if is_win else pm
        try:
            subprocess.run(
                [cmd_name, "--version"],
                capture_output=True,
                check=True,
                cwd=FRONTEND_DIR,
                shell=False # Use false, but explicit cmd_name for Windows
            )
            return [cmd_name, "run", "dev"]
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError("No package manager found (bun/pnpm/npm). Install one first.")


def run(backend: bool = True, frontend: bool = True):
    processes = []

    try:
        if backend:
            print("\n\033[96m[LAUNCHER] 🚀 Starting FastAPI backend on http://localhost:8000 ...\033[0m")
            bp = subprocess.Popen(
                BACKEND_CMD,
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": ROOT},
            )
            processes.append(("Backend", bp))
            time.sleep(2)  # Let backend init before frontend starts

        if frontend:
            fe_cmd = get_frontend_cmd()
            print(f"\n\033[92m[LAUNCHER] 🎨 Starting React frontend with `{' '.join(fe_cmd)}` on http://localhost:5173 ...\033[0m")
            fp = subprocess.Popen(fe_cmd, cwd=FRONTEND_DIR)
            processes.append(("Frontend", fp))

        if backend and frontend:
            print("\n\033[93m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
            print("\033[93m  Backend  → http://localhost:8000\033[0m")
            print("\033[93m  Frontend → http://localhost:5173\033[0m")
            print("\033[93m  API Docs → http://localhost:8000/docs\033[0m")
            print("\033[93m  Press Ctrl+C to stop all services\033[0m")
            print("\033[93m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")

        # Wait indefinitely — Ctrl+C exits
        for _, proc in processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\n\033[91m[LAUNCHER] ⛔ Shutdown signal received. Stopping all services...\033[0m")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                print(f"\033[91m[LAUNCHER] Terminating {name}...\033[0m")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("\033[91m[LAUNCHER] ✅ All services stopped.\033[0m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CIS V3 — Start all services")
    parser.add_argument("--backend-only",  action="store_true", help="Start backend only")
    parser.add_argument("--frontend-only", action="store_true", help="Start frontend only")
    args = parser.parse_args()

    backend  = not args.frontend_only
    frontend = not args.backend_only

    run(backend=backend, frontend=frontend)
