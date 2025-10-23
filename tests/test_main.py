import pytest
import os
import shutil
import gc  # <-- Perbaikan 1: Impor Garbage Collector
from fastapi.testclient import TestClient
from src.main import app, STATS  # <-- Impor STATS untuk di-reset
from src import database

# Nama folder tes khusus untuk database
TEST_DB_DIR = "test_data"
TEST_DB_FILE = os.path.join(TEST_DB_DIR, "aggregator.db")

@pytest.fixture(scope="function")
def test_client(monkeypatch):
    """
    Fixture ini adalah 'setup' dan 'teardown' untuk setiap tes.
    """
    
    # --- Perbaikan 2: Reset stats in-memory di awal setiap tes ---
    STATS["received"] = 0
    STATS["duplicate_dropped"] = 0
    # --- Akhir Perbaikan 2 ---
    
    # 1. (Monkeypatch) Alihkan database.py untuk menggunakan DB tes
    monkeypatch.setattr(database, "DB_DIR", TEST_DB_DIR)
    monkeypatch.setattr(database, "DB_FILE", TEST_DB_FILE)
    
    # 2. Hapus folder database tes LAMA (jika ada) dan buat yang baru
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR)
    os.makedirs(TEST_DB_DIR, exist_ok=True)
    
    # 3. Inisialisasi database (sekarang menunjuk ke folder tes)
    database.init_db()

    # 4. Sediakan 'client' agar tes bisa memanggil API
    client = TestClient(app)
    yield client  # Tes akan berjalan di sini

    # 5. (Teardown) Tutup client SEBELUM hapus file
    client.close()

    # --- Perbaikan 3: Paksa Garbage Collection untuk melepaskan kunci file ---
    gc.collect()
    # --- Akhir Perbaikan 3 ---

    shutil.rmtree(TEST_DB_DIR)

# --- Mulai Tes (Tidak ada perubahan di sini) ---

# (Tes 1) Mengirim event baru
def test_publish_new_event(test_client):
    event = {
        "topic": "testing", "event_id": "test-001", "timestamp": "2025-01-01T00:00:00Z",
        "source": "pytest", "payload": {"data": 1}
    }
    response = test_client.post("/publish", json=event)
    assert response.status_code == 200
    assert response.json()["newly_processed"] == 1
    assert response.json()["duplicates_dropped_in_batch"] == 0

# (Tes 2) Tes Deduplikasi (Paling Penting)
def test_deduplication(test_client):
    event = {
        "topic": "testing", "event_id": "test-002", "timestamp": "2025-01-01T00:00:00Z",
        "source": "pytest", "payload": {"data": 2}
    }
    
    # Kirim pertama kali
    response1 = test_client.post("/publish", json=event)
    assert response1.status_code == 200
    assert response1.json()["newly_processed"] == 1

    # Kirim kedua kali (duplikat)
    response2 = test_client.post("/publish", json=event)
    assert response2.status_code == 200
    assert response2.json()["newly_processed"] == 0
    assert response2.json()["duplicates_dropped_in_batch"] == 1

# (Tes 3) Tes Endpoint /stats
def test_stats_endpoint(test_client):
    # Cek stats awal (kosong)
    stats1 = test_client.get("/stats").json()
    assert stats1["persistent_stats (from_db)"]["total_unique_events_processed"] == 0

    # Kirim 3 event (2 unik, 1 duplikat)
    event1 = {"topic": "t1", "event_id": "e1", "timestamp": "...", "source": "s1", "payload": {}}
    event2 = {"topic": "t1", "event_id": "e2", "timestamp": "...", "source": "s1", "payload": {}}
    event3_dup = event1 # Ini duplikat dari event1
    
    test_client.post("/publish", json=[event1, event2, event3_dup])
    
    # Cek stats akhir
    stats2 = test_client.get("/stats").json()
    assert stats2["runtime_stats (in-memory)"]["total_events_received"] == 3
    assert stats2["runtime_stats (in-memory)"]["total_duplicate_events_dropped"] == 1
    assert stats2["persistent_stats (from_db)"]["total_unique_events_processed"] == 2
    assert "t1" in stats2["persistent_stats (from_db)"]["known_topics"]

# (Tes 4) Tes Endpoint /events
def test_get_events(test_client):
    event = {
        "topic": "topic-get", "event_id": "get-001", "timestamp": "2025-01-01T00:00:00Z",
        "source": "pytest", "payload": {"data": "test-get"}
    }
    test_client.post("/publish", json=event)
    
    # Ambil event
    response = test_client.get("/events?topic=topic-get")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["event_id"] == "get-001"
    assert data["events"][0]["source"] == "pytest"

# (Tes 5) Tes Validasi Skema (kirim data buruk)
def test_bad_schema(test_client):
    # Event ini 'event_id' nya hilang, harusnya gagal
    event_missing_id = {
        "topic": "testing", "timestamp": "2025-01-01T00:00:00Z",
        "source": "pytest", "payload": {"data": 1}
    }
    response = test_client.post("/publish", json=event_missing_id)
    # 422 Unprocessable Entity adalah kode error validasi dari FastAPI
    assert response.status_code == 422