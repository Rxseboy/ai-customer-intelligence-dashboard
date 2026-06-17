# 🔐 Panduan Keamanan: Row-Level Security (RLS) & Multi-Tenancy

Dokumen ini menjelaskan cara mengamankan database Supabase agar RAG AI Assistant **tidak bisa membocorkan data antar-tenant** (multi-store/multi-client), serta panduan membuat user Read-Only PostgreSQL yang proper.

---

## Mengapa Ini Penting?

Sistem RAG Text-to-SQL menggunakan LLM untuk men-generate query SQL secara dinamis. Tanpa pengamanan di level database, ada risiko:

1. **Prompt Injection** — User bisa mencoba memanipulasi LLM agar mengakses data sensitif
2. **Data Leakage** — Jika sistem berkembang menjadi SaaS multi-toko, query LLM dari Toko A bisa tidak sengaja melihat data Toko B
3. **DML Injection** — Meski sudah ada `SQLSafetyValidator` di Python, pengamanan berlapis di DB lebih aman

---

## Bagian 1: Membuat User PostgreSQL Read-Only

### Langkah di Supabase SQL Editor

Buka **Supabase Dashboard → SQL Editor** dan jalankan perintah berikut:

```sql
-- 1. Buat user read-only khusus untuk RAG
CREATE USER readonly_user WITH PASSWORD 'ganti_dengan_password_kuat';

-- 2. Berikan akses CONNECT ke database
GRANT CONNECT ON DATABASE postgres TO readonly_user;

-- 3. Berikan akses USAGE ke schema public
GRANT USAGE ON SCHEMA public TO readonly_user;

-- 4. Berikan hak SELECT ONLY ke semua tabel yang ada sekarang
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- 5. Pastikan tabel baru di masa depan juga otomatis dapat akses SELECT
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO readonly_user;
```

### Update file `.env`

```env
# Gunakan readonly_user untuk koneksi RAG
DATABASE_URL_READONLY=postgresql://readonly_user.[PROJECT_ID]:password_kuat@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
```

> ⚠️ **PENTING**: Jangan pernah menggunakan user `postgres` (superuser) untuk koneksi RAG. Selalu gunakan `readonly_user`.

---

## Bagian 2: Mengaktifkan Row-Level Security (RLS) untuk Multi-Tenancy

RLS memungkinkan PostgreSQL memfilter baris data secara otomatis berdasarkan **siapa yang sedang login**, bahkan sebelum query dari LLM dieksekusi.

### Skenario: Sistem Digunakan oleh Beberapa Toko (SaaS)

Asumsi: Setiap toko memiliki kolom `tenant_id` di setiap tabel.

### Langkah 1 — Aktifkan RLS di semua tabel

```sql
-- Aktifkan RLS
ALTER TABLE dim_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_orders   ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_products  ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_date      ENABLE ROW LEVEL SECURITY;
```

### Langkah 2 — Buat Policy per Tabel

```sql
-- Policy: User hanya bisa SELECT baris milik tenant mereka sendiri
-- dim_customers
CREATE POLICY tenant_isolation_customers ON dim_customers
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);

-- fact_orders
CREATE POLICY tenant_isolation_orders ON fact_orders
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);
```

### Langkah 3 — Set Tenant ID di Setiap Sesi RAG

Di Python, sebelum menjalankan query RAG, set `app.current_tenant_id` di sesi PostgreSQL:

```python
from sqlalchemy import text

def get_tenant_db(tenant_id: int, base_url: str):
    """Buat SQLDatabase connection dengan tenant context."""
    from sqlalchemy import create_engine, event
    from langchain_community.utilities import SQLDatabase

    engine = create_engine(base_url)

    # Set tenant ID di setiap koneksi baru
    @event.listens_for(engine, "connect")
    def set_tenant(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET app.current_tenant_id = '{tenant_id}'")
        cursor.close()

    return SQLDatabase(engine)
```

> ✅ Dengan cara ini, **walaupun LLM men-generate `SELECT * FROM dim_customers`**, PostgreSQL akan otomatis menambahkan filter `WHERE tenant_id = [ID_TOKO_YANG_LOGIN]` sebelum data dikembalikan.

---

## Bagian 3: Konfigurasi Supabase Auth (Opsional — untuk Web App)

Jika Anda menggunakan Supabase Auth untuk login user:

```sql
-- Policy menggunakan JWT claim dari Supabase Auth
CREATE POLICY user_data_isolation ON dim_customers
    FOR SELECT
    USING (tenant_id = (auth.jwt() ->> 'tenant_id')::INTEGER);
```

---

## Ringkasan Lapisan Keamanan

```
User Request
    │
    ▼
[1] Pydantic Validation     ← Cek panjang & format pertanyaan
    │
    ▼
[2] SQLSafetyValidator      ← Blokir DML (DROP/DELETE/UPDATE) via Regex berlapis
    │
    ▼
[3] LLM generates SQL       ← Groq Llama 3
    │
    ▼
[4] Self-Correction Loop    ← Retry jika SQL error (max 2x)
    │
    ▼
[5] PostgreSQL RLS          ← Filter baris otomatis berdasarkan tenant_id
    │
    ▼
[6] readonly_user session   ← Tidak punya hak DROP/INSERT/UPDATE di level DB
    │
    ▼
Result → NLG Answer
```

---

*Diperbarui: Mei 2026 | Rizqi Fajar*
