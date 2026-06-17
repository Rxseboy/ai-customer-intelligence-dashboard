# 📊 Analisis Hasil Keluaran Customer Intelligence System

Berdasarkan data yang diproses oleh *Customer Intelligence System* melalui pipeline transformasi, segmentasi RFM (KMeans), dan model prediksi Churn (XGBoost), berikut adalah penjabaran indikator utama dan insight bisnis dari pelanggan *thelook eCommerce*.

## 1. Ringkasan Eksekutif (Key Metrics)

Dari keseluruhan dataset yang diolah, sistem berhasil mengekstraksi dan mengevaluasi profil para pelanggan:
- **Total Pelanggan Terdaftar**: 66.112 pengguna unik
- **Total Pendapatan (Revenue)**: ~$8,06 Juta USD
- Pelanggan dikelompokkan menjadi 4 segmen utama berdasarkan kebiasaan berbelanja (**RFM**: *Recency, Frequency, Monetary*) menggunakan algoritma K-Means Clustering.
- Algoritma prediksi churn menyoroti peringatan yang cukup besar pada metrik retensi pelanggan (customer retention).

---

## 2. Analisis Segmentasi Pelanggan (Customer Segmentation)

Pelanggan diklasifikasikan ke dalam 4 segmen. Hasil menunjukkan distribusi jumlah pelanggan dan kontribusi pendapatan sebagai berikut:

| Segmen | Jumlah Pelanggan | % Pelanggan | Pendapatan (Revenue) | % Kontribusi Pendapatan | Karakteristik Utama |
|---|---|---|---|---|---|
| 🌱 **Potential** | 31.734 | 48,0% | $2.51 Juta | 31,1% | Pelanggan baru/umum yang memiliki aktivitas namun belum tinggi frekuensinya. Merupakan populasi terbesar dengan potensi besar jika diberikan insentif belanja. |
| 💚 **Loyal** | 14.776 | 22,3% | $2.14 Juta | 26,6% | Selalu berbelanja cukup rutin. Memberikan porsi pendapatan yang sangat solid dan aman. |
| ⚠️ **At Risk** | 14.907 | 22,5% | $1.27 Juta | 15,7% | Pernah aktif berbelanja sebelumnya namun sudah sangat lama tidak melakukan transaksi. |
| 🏆 **Champions** | 4.695 | 7,1% | $2.13 Juta | 26,5% | Pelanggan paling setia dengan nilai transaksi paling tinggi. Walaupun hanya **7%** dari populasi pembeli, tapi menyumbang lebih dari **26% pendapatan**. |

> [!TIP]
> **Peluang Bisnis (Pareto Effect):** Terlihat jelas efek pareto di mana sebagian kecil pengguna (grup *Champions* + *Loyal*) berjumlah ~29% dari keseluruhan, tetapi berhasil mendominasi lebih dari 53% total pendapatan perusahaan. Fokus menjaga kepuasan segmen ini akan menjadi fondasi revenue yang stabil.

---

## 3. Analisis Risiko Kehilangan Pelanggan (Churn Prediction)

Prediksi churn menggunakan *XGBoost* menghasilkan penilaian level risiko *(Risk Level)* bagi setiap profil. Hasil keluaran model memberikan sinyal peringatan *(alert)* yang kritis untuk bisnis ini:

- 🔴 **High Risk (Risiko Tinggi Churn)**: 59.160 Pelanggan (~89,4%)
- 🟢 **Low Risk (Risiko Rendah Churn)**: 6.952 Pelanggan (~10,5%)

**Total Nilai Revenue yang Berada Dalam Risiko (*Revenue at Risk*):** **$7,11 Juta USD** (88% dari revenue historis riil).

> [!WARNING]
> **Tingkat Retensi yang Rendah:** Angka risiko Churn sebesar 89% mengindikasikan bahwa *thelook eCommerce* berjalan dalam pola "Pembeli Satu Kali / One-Time Buyers". Banyak dari pengguna melakukan pendaftaran, berbelanja sekali atau sedikit, lalu tidak pernah terlihat kembali dalam waktu 30+ hari terakhir *(Recency memburuk)*. 

---

## 4. Rekomendasi Tindak Lanjut (Actionable Insights)

Dengan adanya insight otomatis ini, tim pemasaran dan produk dapat melakukan berbagai langkah konkret untuk memperbaiki efisiensi bisnis:

### A. Strategi Retensi Berdasarkan Segmen
1. **Champions & Loyal (VIP Treatment)**: Buatkan kelompok "Loyalty Program" khusus dengan akses produk lebih awal (*early access*), program pengembalian bebas biaya, dan diskon premium di transaksi bernilai besar. Tujuannya adalah mempertahankan mereka tetap berada di level hijau (🟢 *Low Risk*).
2. **Potential Buyers (Onboarding & Nurturing)**: Lebih dari 48% pelanggan ada di segmen ini. Jangan biarkan mereka berpindah ke *At Risk*. Gunakan push notification app / email marketing dengan promo *Free Shipping* (gratis ongkir) atau diskon silang (*cross-selling*) untuk meningkatkan Frequency belanja harian/mingguan mereka.
3. **At Risk (Win-back Campaigns)**: Mengingat $1,2 Juta USD uang pernah keluar dari dompet mereka, kita perlu mengingatkan eksistensi brand kita. Kirimkan pesan promosi spesifik ("*We miss you! Here is a 20% off your next order*") untuk menghidupkan kembali minat belanja pelanggan tersebut.

### B. Evaluasi Fundamental Bisnis
Karena 89% kelompok masuk daftar "High Churn Risk", ada indikasi evaluasi bisnis harus digeser dari "Hanya fokus *Acquisition* pengguna baru" menjadi "**Fokus menjaga pelanggan tetap berbelanja (*Retention*)**". Cek kembali variabel seperti: kualitas barang (*product defects*), respons *customer service*, hingga biaya ongkir yang terlalu tinggi yang membuat pelanggan enggan kembali ke *platform*.

---
*(Laporan ini merupakan ringkasan analitik dari data riil keluaran pipeline machine learning dan diproduksi secara otomatis sebagai penunjang keputusan eksekutif)*
