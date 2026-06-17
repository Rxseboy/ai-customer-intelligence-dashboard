# 🤖 RAG AI Assistant Test Prompt Catalog
### E-Commerce Customer Intelligence System V3

Selamat datang di katalog pengujian RAG (Text-to-SQL) Asisten AI. Dokumen ini dirancang untuk menguji kecerdasan, pemahaman konteks, tingkat kompleksitas query SQL yang di-generate, serta performa pengambilan data dari PostgreSQL / BigQuery dari tingkat pemula hingga tingkat mahir.

---

## 🟢 1. Tingkat Pemula (Beginner - Deskriptif Sederhana)
*Fokus: Menguji kemampuan AI dalam melakukan query SELECT dasar, agregasi sederhana (SUM, COUNT), filtering tanggal standar, dan pencarian kategori.*

| No | Prompt Pengujian | Tujuan Bisnis & Ekspektasi SQL |
|---|---|---|
| **1.1** | `Berapa total revenue sepanjang tahun 2023?` | Menghitung total nilai transaksi (`SUM(sale_price)`) pada tahun 2023 dengan filter waktu. |
| **1.2** | `Berapa jumlah transaksi atau order yang masuk di bulan Januari 2024?` | Menghitung total transaksi unik (`COUNT(DISTINCT order_id)`) dengan filter bulan spesifik. |
| **1.3** | `Tampilkan 5 kategori produk dengan jumlah transaksi terbanyak!` | Menggunakan `GROUP BY` kategori produk, diurutkan descending, dengan limitasi data (`LIMIT 5`). |
| **1.4** | `Berapa jumlah customer unik yang terdaftar di database?` | Melakukan `COUNT(DISTINCT customer_id)` dari tabel profil pelanggan. |

*💡 **Tips Pengujian:** Perhatikan apakah RAG mengenali kolom tanggal (misal `created_at` atau `order_date`) dan menerapkan filter tahun/bulan dengan benar.*

---

## 🟡 2. Tingkat Menengah (Intermediate - Agregasi & Join Multi-Tabel)
*Fokus: Menguji pemahaman AI terhadap relasi antar tabel (JOIN antara customer, orders, dan product_items), perhitungan rasio rata-rata (AOV), dan pemeringkatan dasar.*

| No | Prompt Pengujian | Tujuan Bisnis & Ekspektasi SQL |
|---|---|---|
| **2.1** | `Siapa top 5 customer berdasarkan total nilai belanja sepanjang waktu?` | Melakukan `JOIN` antara tabel customer dan orders, mengelompokkan berdasarkan nama/ID customer, menjumlahkan spend, dan mengambil 5 teratas. |
| **2.2** | `Tampilkan performa bulanan (total revenue dan total order) selama tahun 2023.` | Mengelompokkan transaksi per bulan (`DATE_TRUNC` atau extract month), menghitung metrik revenue dan jumlah order, urut kronologis. |
| **2.3** | `Apa saja 5 brand produk dengan rata-rata harga jual termahal?` | Mengelompokkan berdasarkan kolom brand, menghitung `AVG(sale_price)`, dan diurutkan dari yang tertinggi. |
| **2.4** | `Hitung rata-rata nilai keranjang belanja (Average Order Value / AOV) per bulan selama semester pertama tahun 2024.` | Membagi total revenue bulanan dengan total order unik bulanan (`SUM(price) / COUNT(DISTINCT order_id)`) untuk bulan Jan-Jun 2024. |

---

## 🔵 3. Tingkat Lanjut (Advanced - Segmentasi, Cohort, & Window Functions)
*Fokus: Menguji logika analitik yang lebih dalam seperti cohort customer, analisis perilaku repeat purchase, perbandingan antar segmen RFM, dan penyaringan segmentasi prediktif.*

| No | Prompt Pengujian | Tujuan Bisnis & Ekspektasi SQL |
|---|---|---|
| **3.1** | `Bandingkan rata-rata transaksi dan total spend untuk setiap segmen customer (Champion, Loyal, At Risk, Lost).` | Mengelompokkan customer berdasarkan tag segmen RFM mereka dan menghitung metrik performa masing-masing segmen. |
| **3.2** | `Berapa persentase customer yang melakukan repeat order (beli lebih dari 1 kali)?` | Menggunakan subquery atau CTE untuk menghitung total customer yang memiliki frekuensi order > 1, kemudian dibagi dengan total seluruh customer. |
| **3.3** | `Tampilkan kontribusi persentase revenue bulanan untuk setiap kategori produk selama 6 bulan terakhir.` | Menggunakan Window Function `SUM(revenue) OVER (PARTITION BY month)` untuk membagi penjualan kategori dengan total penjualan bulan tersebut. |
| **3.4** | `Siapa saja 10 customer berstatus 'At Risk' dengan nilai estimasi CLV (Customer Lifetime Value) tertinggi?` | Melakukan join tabel segmen RFM dengan tabel prediktif CLV (Gamma-Gamma/BG-NBD) untuk menyaring pelanggan berisiko tinggi yang bernilai tinggi secara finansial. |

---

## 🟣 4. Tingkat Ahli (Expert / Guru - Analisis Prediktif & Probabilitas)
*Fokus: Menguji integrasi antara tabel transaksi aktual dengan output model Machine Learning (nilai probabilitas aktif BG/NBD, prediksi CLV 12 bulan, dan rekomendasi produk).*

| No | Prompt Pengujian | Tujuan Bisnis & Ekspektasi SQL |
|---|---|---|
| **4.1** | `Bandingkan rata-rata nilai order aktual dengan nilai moneter estimasi dari model Gamma-Gamma untuk segmen Champion.` | Mengukur akurasi model ML dengan membandingkan nilai transaksi historis rata-rata dengan nilai prediksi moneter (`expected_average_profit`). |
| **4.2** | `Siapa customer dengan probability of being active (p_active) terendah di bawah 20% yang sebelumnya bertransaksi di kategori 'Fashion'?` | Mencari target customer untuk re-engagement campaign dengan memfilter output model BG/NBD (`p_active < 0.2`) dikombinasikan dengan histori kategori item. |
| **4.3** | `Hitung rata-rata waktu jeda antar pembelian (inter-purchase time dalam hari) untuk customer di cluster Champion.` | Menggunakan lead/lag window functions untuk menghitung selisih hari antara order berurutan per customer, kemudian merata-ratakannya untuk segmen Champion. |

---

## 🛠️ Cara Melakukan Pengujian di Dashboard
1. Buka dashboard E-Commerce Customer Intelligence.
2. Klik tombol **💬** di pojok kanan bawah untuk membuka **Tanya AI Instan**, atau masuk ke **Tab 5: RAG Assistant**.
3. Salin salah satu prompt di atas dan tempelkan ke input chat.
4. Klik **Kirim ⚡**.
5. Buka accordion **🛠️ View Executable SQL Query** untuk memverifikasi kebenaran syntax SQL yang dibuat oleh AI.
6. Bandingkan output visual tabel dengan ekspektasi bisnis Anda!
