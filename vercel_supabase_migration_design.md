# Desain Migrasi Vercel & Supabase

## 1. Ringkasan Pemahaman (Understanding Summary)
* **Apa yang dibangun:** Migrasi arsitektur dari aplikasi web registrasi dan pemindaian tiket (berbasis Flask).
* **Mengapa ini dilakukan:** Agar aplikasi dapat di-deploy di Vercel (serverless) dengan menggunakan Supabase (PostgreSQL) sebagai database permanen.
* **Untuk siapa ini:** Panitia penyelenggara acara (admin) dan peserta (pendaftar tiket).
* **Batasan Utama:** Aplikasi akan tetap menggunakan kerangka kerja Python (Flask). Pengaturan kredensial database dilakukan melalui Environment Variables, bukan hardcode.
* **Bukan Tujuan (Non-Goals):** Tidak menambahkan fitur baru, tidak merombak antarmuka pengguna (UI), dan tidak mengubah framework dari Flask ke framework lain.

## 2. Asumsi
* Skala lalu lintas data akan cukup ditangani dengan aman oleh paket gratis (Free Tier) dari Vercel dan Supabase.
* Keterlambatan sesaat (cold start ~1-2 detik) saat pertama kali membuka aplikasi dapat diterima.

## 3. Catatan Keputusan (Decision Log)
1. **Keputusan Framework:** Tetap mempertahankan Python/Flask daripada menulis ulang menggunakan Next.js.
   * *Alasan:* Pengembangan jauh lebih cepat, stabil, dan menghindari risiko modifikasi logika bisnis berlebihan.
2. **Keputusan Koneksi Database:** Menggunakan SQLAlchemy + `psycopg2-binary` alih-alih menggunakan Supabase-py REST API.
   * *Alasan:* Melindungi kode aplikasi (`app.py`) dari perombakan besar; ekstensi tinggi; dan standardisasi industri.
3. **Keputusan Arsitektur Vercel:** Menggunakan file konfigurasi `vercel.json` dan `requirements.txt`.
   * *Alasan:* Cara standar bagi Vercel untuk mendeteksi runtime `@vercel/python`.
4. **Keputusan Keamanan dan Stabilitas Serverless:** Menggunakan URL *Connection Pooler* dari Supabase.
   * *Alasan:* Untuk mencegah *connection exhaustion* saat puluhan instance Vercel dihidupkan secara bersamaan dalam kondisi lalu lintas tinggi.

## 4. Desain Akhir (Final Design)
1. **Kebutuhan Repositori:**
   - Menambahkan file `vercel.json` yang mengalihkan lalu lintas (rewrites) ke aplikasi Flask.
   - Menambahkan file `requirements.txt` dengan dependensi `Flask`, `Flask-SQLAlchemy`, `Flask-Login`, `psycopg2-binary`.
2. **Penyesuaian Kode (`app.py`):**
   - Mengganti URI konfigurasi database untuk mengambil dari variabel lingkungan (`os.environ.get('DATABASE_URL')`).
   - Memastikan app secret key diambil dari environment (`os.environ.get('SECRET_KEY')`).
3. **Langkah Inisialisasi:**
   - Membuat skema tabel (User, Tiket, Setting) di Supabase menggunakan instance SQL interaktif atau dengan menjalankan script sinkronisasi satu kali (`db.create_all()`).
4. **Strategi Pengujian:**
   - Menguji secara lokal dengan `.env` (python-dotenv) ke database live Supabase.
   - Menjalankan `vercel dev` untuk pengujian CLI sebelum melakukan push dan deploy ke platform live.
