# ==============================================================================
# HUGGING FACE DOCKERFILE OVERRIDE
# Menarik environment ringan dan instalasi paket minimal untuk FastAPI saja
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# 1. Install System Dependensi
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy Requirements
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy Seluruh Proyek
COPY . .

# 4. Hugging Face Spaces MEWAJIBKAN port layanan berada di angka 7860
EXPOSE 7860

# 5. Permission fallback
RUN mkdir -p /tmp/cache && chmod 777 /tmp/cache
ENV NUMBA_CACHE_DIR=/tmp/cache

# 6. Override Perintah Utama! (Jalankan Uvicorn FastAPI)
CMD ["uvicorn", "src.back_end.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
