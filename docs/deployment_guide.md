# 🚀 Panduan Deployment API di Hugging Face Spaces

Dokumen ini menjelaskan langkah-demi-langkah (Setup & Deploy) untuk mendeploy **FastAPI Backend (Customer Intelligence)** ke dalam ekosistem [Hugging Face Spaces](https://huggingface.co/spaces) secara gratis, tanpa kartu kredit, dan dengan kapasitas RAM yang memadai (16 GB) untuk kebutuhan Machine Learning.

---

## 1. Persiapan Awal (Pembuatan Space)

1. Buka browser dan login ke akun [Hugging Face](https://huggingface.co/join).
2. Di pojok kanan atas, klik foto profil Anda lalu pilih menu **New Space**.
3. Isi formulir pembuatan:
   - **Space name**: `customer-intelligence-api` (bebas)
   - **License**: `mit` atau `apache-2.0`
   - **Select the Space SDK**: Pilih ikon **Docker** (lalu pilih *Blank*).
   - **Space Hardware**: Biarkan default "Free" (2 vCPU, 16GB RAM).
4. Klik tombol **Create Space**.

---

## 2. Pengaturan Variabel Lingkungan (Secrets)

Kredensial database tidak boleh ditulis di dalam kode. Anda harus mendaftarkannya di fitur rahasia Hugging Face:

1. Di halaman Space yang baru saja dibuat, klik tombol ⚙️ **Settings** di pojok kanan atas.
2. Scroll ke bawah hingga menemukan menu **Variables and secrets**.
3. Klik tombol **New secret** untuk Database:
   - **Name**: `DATABASE_URL`
   - **Value**: `postgresql://[USER_SUPABASE]:[PASS]@[HOST_SUPABASE]:6543/postgres`
4. *(Opsional: Jika API Anda akan melakukan query langsung ke BigQuery (tidak melalui Airflow))* Klik **New secret** lagi untuk BigQuery:
   - **Name**: `GOOGLE_APPLICATION_CREDENTIALS`
   - **Value**: `key.json`

---

## 3. Merancang Dockerfile Spesifik Hugging Face

Karena *Repository Github* lokal Anda secara otomatis menggunakan `Dockerfile` yang memuat Apache Airflow, maka agar sistem mematuhi **port 7860** wajib Hugging Face tanpa merusak arsitektur lokal, buatlah sebuah file baru bernama **`Dockerfile.hf`** secara lokal di komputer (tempatkan sejajar dengan files `README.md`).

Isi dari **`Dockerfile.hf`** adalah:

```dockerfile
# ==============================================================================
# HUGGING FACE DOCKERFILE OVERRIDE
# Menarik environment ringan dan instalasi paket minimal untuk FastAPI saja
# ==============================================================================
FROM python:3.10-slim

WORKDIR /app

# 1. Install System Dependensi
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy Requirements Minimalis API
COPY api/requirements.txt requirements.txt
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
```

Commit file `Dockerfile.hf` tersebut di lokal Anda dengan:
`git add Dockerfile.hf`
`git commit -m "Tambahkan Dockerfile.hf untuk deployment Hugging Face"`

---

## 4. Konfigurasi Path dan Mengunggah Kode

Sekarang, Anda masuk ke tahap krusial dimana file konfigurasi dan kode dikunci bersemayam di Hugging Face Server.

1. Simpan repositori **Hugging Face** Space milik Anda di *remote* komputer dengan menjalankan:
   ```bash
   git remote add huggingface https://huggingface.co/spaces/UsernameHuggingFaceAnda/customer-intelligence-api
   ```
2. Cukup unggah langsung (Push):
   ```bash
   git push huggingface main --force
   ```
   *(Harap diingat, Hugging Face **meminta Access Token** sebagai password ketika dipush via terminal. Silakan generate *Write* token Anda di halaman Settings profile HF).*
3. Setelah semuanya berhasil ter-upload:
   - Di web Hugging Face layar Space Anda, klik tombol ⚙️ **Settings**.
   - Terus gulir ke bawah pada menu Settings sampai menemukan sub-menu konfigurasi **"Dockerfile file path"**.
   - Secara bawaan tertulis `Dockerfile`. **Ubah bagian ini dan isikan menjadi `Dockerfile.hf`**.
   - Tekan enter (Sistem Hugging Face akan merestart Build saat terjadi *update*).

## 5. Pemantauan & Pengecekan

1. Setalah *push* terminal di VSCode berhasil, kembali ke website Hugging Face Space Anda.
2. Status di ujung atas akan berubah menjadi kuning bertuliskan **Building**. Ini normal, Hugging Face sedang mengerahkan 16GB RAM-nya untuk menginstal XGBoost, FastApi, dan Scikit-Learn Anda yang memakan waktu 3 - 5 menit.
3. Silakan sorot tab **Logs** jika Anda penasaran dengan proses berjalannya.
4. Ketika sudah selesai, log akan tertulis *"Uvicorn running on http://0.0.0.0:7860"*, dan status Space Anda akan berubah hijau menjadi **Running**.
5. Pada titik ini, aplikasi Anda resmi mengudara! (Hanya klik dan buka *URL Embed* yang disediakan Hugging Face untuk diintegrasikan pada aplikasi Frontend lain).

---
<br>

# 📊 Panduan Deployment Streamlit Dashboard

Setelah berhasil menghidupkan *Back-end* (FastAPI) di Hugging Face, sekarang saatnya membangkitkan tata ruang visual (*Front-end* Streamlit) Anda.

Sebagai standar emas dalam komunitas Data Science, **menyebarkan Dashboard Streamlit dari satu repository MLOps sangat disarankan menggunakan [Streamlit Community Cloud](https://share.streamlit.io/).** Ini 100% gratis, dirancang khusus oleh pembuat Streamlit, dan sangat cepat!

### Langkah-langkah Streamlit Cloud:

1. **Pastikan GitHub Anda Update**  
   Simpan dan unggah (`git push origin main`) seluruh riwayat kode Anda ke GitHub utama (`github.com/Rxseboy/E-Commerce-Customer-Intelligence-System`).

2. **Login ke Streamlit**  
   Buka [share.streamlit.io](https://share.streamlit.io/) dan buat akun menggunakan GitHub Anda untuk menghubungkan data dengan aman.

3. **Deploy Aplikasi Baru**  
   - Di kanan atas layar, tekan tombol biru **"New app"**.
   - Pilih opsi **"Use existing repo"**.

4. **Isi Formulir Aplikasi**  
   - **Repository:** Cari dan pilih Repo GitHub Anda.
   - **Branch:** `main`
   - **Main file path:** Di sinilah Streamlit mencari jantung program visual Anda. Ubah `streamlit_app.py` bawaan dan ketik persis ini:  
     `src/front_end/dashboard.py`
   - **App URL:** (Opsi, Anda bisa merancang *custom link* seperti `ecommerce-intelligence.streamlit.app`).

5. **Masukkan Secret Keys (SANGAT PENTING!)**  
   Jangan langsung klik Deploy! Karena Dashboard kita juga menarik data langsung ke PostgreSQL Cloud, kita wajib mengamankan kredensialnya:
   - Klik panah `Advanced settings...` (Pengaturan lanjutan).
   - Akan terbuka jendela gelap ber-struktur [TOML/YAML].  
   - Tempelkan *Secrets* database Anda berdasarkan patokan `.env`:
     ```toml
     DB_USER="postgres"
     DB_PASSWORD="adminpass_supabase_anda"
     DB_HOST="aws-x-x-x.supabase.com"
     DB_PORT="5432"
     DB_NAME="postgres"
     ```
   - Tekan **Save**.

6. **Luncurkan (Deploy)**
   Kini Anda tinggal menekan tombol biru **Deploy!**. Streamlit Cloud akan memutar mesin untuk menginstall requirements dan secara ajaib menampilkan animasi pembuatan *Dashboard*!

Dashboard portofolio visual Anda kini online di internet publik menemani layanan *Microservice FastApi*!
