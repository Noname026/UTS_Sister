# UTS Sistem Terdistribusi - Log Aggregator Idempotent

nama :Hanafi Mas'uul Prastyadi
NIM : 11221022
Mata Kuliah : Sistem Paralel dan Terdistribusi - UTS

Ini adalah implementasi untuk Ujian Tengah Semester Sistem Terdistribusi, yang berfokus pada pembuatan layanan *log aggregator* dengan *consumer* yang *idempotent* dan *deduplication* untuk menangani *at-least-once delivery semantics*.

Proyek ini dibangun menggunakan Python (FastAPI), SQLite untuk penyimpanan persisten, dan di-container-isasi penuh menggunakan Docker dan Docker Compose.

**Link Video Demo YouTube:** [(https://youtu.be/vz2wsTjlIH8)]

---

## Fitur Utama

* **API (FastAPI)**: Menyediakan *endpoint* untuk menerima (`/publish`), melihat (`/events`), dan memonitor (`/stats`) log.
* **Idempotency & Deduplication**: Menjamin setiap *event* dengan `(topic, event_id)` yang sama hanya diproses satu kali, bahkan jika diterima berkali-kali.
* **Persistensi**: Menggunakan SQLite yang disimpan dalam Docker Volume (`aggregator-data`) untuk memastikan "ingatan" deduplikasi tidak hilang saat *container* di-restart.
* **Unit Tests**: Mencakup 5 tes (`pytest`) untuk validasi fungsional, termasuk deduplikasi dan validasi skema.
* **Skala Uji**: Dilengkapi skrip `stress_test.py` untuk membuktikan sistem dapat menangani 5.000+ *event* (dengan 20% duplikasi) secara efisien.
* **Bonus Docker Compose**: Menyediakan `docker-compose.yml` untuk menjalankan *service* `aggregator` dan *service* `publisher` secara bersamaan dalam satu jaringan internal.

---

## Cara Menjalankan (Rekomendasi - dengan Bonus Docker Compose)

Metode ini akan menjalankan server `aggregator` DAN skrip `publisher_bonus` secara otomatis.

1.  **Build dan Run Services:**
    Pastikan Docker Desktop sedang berjalan, lalu jalankan:
    ```bash
    docker-compose up --build
    ```

2.  **Verifikasi:**
    Anda akan melihat log dari `publisher-service` (mengirim 3 *event*) dan `aggregator-service` (menerima 3 *event* dan mendeteksi 1 duplikat) secara bersamaan.

3.  **Akses API:**
    Server akan tetap berjalan di `http://127.0.0.1:8080`.
    * **Dokumentasi API**: `http://127.0.0.1:8080/docs`
    * **Cek Stats**: `http://127.0.0.1:8080/stats` (Anda akan melihat 3 *event* diterima, 2 unik diproses).

4.  **Untuk Berhenti:**
    Tekan `Ctrl + C` di terminal. Untuk membersihkan *container* (tapi *volume* aman), jalankan:
    ```bash
    docker-compose down
    ```

---

## Cara Menjalankan (Manual - Tanpa Bonus)

Gunakan metode ini jika Anda ingin menjalankan server secara manual untuk pengujian (seperti `stress_test.py` atau "Tes Persistensi").

1.  **Hapus Volume Lama (Opsional tapi direkomendasikan untuk tes bersih):**
    ```bash
    docker volume rm aggregator-data
    ```

2.  **Build Image Docker:**
    ```bash
    docker build -t uts-aggregator .
    ```

3.  **Run Container (dengan Volume Persisten):**
    ```bash
    docker run -p 8080:8080 --rm --name my-aggregator -v aggregator-data:/app/data uts-aggregator
    ```
    Server sekarang berjalan di `http://127.0.0.1:8080`.

---

## Pengujian

### 1. Menjalankan Unit Tests

Pastikan *virtual environment* (`venv`) Anda aktif.

```bash
# Instal dependensi tes (jika belum)
pip install pytest pytest-asyncio httpx

# Jalankan tes
pytest
```
Anda akan melihat output `5 passed`.

### 2. Menjalankan Stress Test (5.000 Event)

Metode ini membuktikan sistem dapat lolos spesifikasi "Performa Minimum".

1.  Pastikan *container* `aggregator` sedang berjalan (menggunakan metode `docker run` atau `docker-compose up`).
2.  Buka terminal **kedua** (dengan `venv` aktif).
3.  Jalankan skrip tes:
    ```bash
    python stress_test.py
    ```
    Anda akan melihat output `VERIFIKASI SUKSES! ✅` setelah selesai.

---

## Endpoint API

* `POST /publish`
    * Menerima satu atau *batch* *event* JSON.
    * Melakukan validasi skema dan deduplikasi.
* `GET /events?topic={nama_topic}`
    * Mengembalikan semua *event* unik yang telah diproses untuk topik tertentu.
* `GET /stats`
    * Menampilkan statistik *runtime* (in-memory) dan statistik persisten (dari database), termasuk `uptime`, `total_events_received`, `total_unique_events_processed`, dan `total_duplicate_events_dropped`.