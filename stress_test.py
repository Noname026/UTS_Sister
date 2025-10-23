import httpx
import asyncio
import time
import uuid
import random

# --- Konfigurasi ---
BASE_URL = "http://127.0.0.1:8080"
TOTAL_EVENTS = 5000
DUPLICATE_PERCENTAGE = 0.20

# --- PERBAIKAN: Batasi koneksi simultan ---
# Kita batasi skrip ini agar hanya 100 permintaan yang berjalan bersamaan
MAX_CONCURRENT_REQUESTS = 100
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# --- Data Event (Sama seperti sebelumnya) ---
num_unique_events = int(TOTAL_EVENTS * (1 - DUPLICATE_PERCENTAGE))
unique_ids = [str(uuid.uuid4()) for _ in range(num_unique_events)]
event_list = []
for i in range(TOTAL_EVENTS):
    if i < num_unique_events:
        event_id = unique_ids[i]
    else:
        event_id = random.choice(unique_ids)
            
    event_list.append({
        "topic": "stress-test",
        "event_id": event_id,
        "timestamp": "2025-10-24T00:00:00Z",
        "source": "stress-tester",
        "payload": {"index": i}
    })

async def send_event(client, event):
    """Kirim satu event, tapi gunakan 'semaphore' untuk membatasi concurrency"""
    
    # --- PERBAIKAN: Tunggu giliran ---
    async with semaphore:
        try:
            await client.post("/publish", json=event, timeout=10)
        except Exception as e:
            # Kita tetap print error jika ada, tapi harusnya sekarang tidak ada
            print(f"Error sending {event['event_id']}: {e}")

async def main():
    print(f"--- Memulai Stress Test (Dibatasi {MAX_CONCURRENT_REQUESTS} req/detik) ---")
    print(f"Total Event: {TOTAL_EVENTS}")
    print(f"Duplikasi: {DUPLICATE_PERCENTAGE * 100}%")
    print(f"Event Unik: {num_unique_events}")
    print(f"Mengirim ke {BASE_URL}...")
    
    start_time = time.time()
    
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        tasks = []
        for event in event_list:
            tasks.append(send_event(client, event))
        
        await asyncio.gather(*tasks)
            
    end_time = time.time()
    
    print("\n--- Tes Selesai ---")
    print(f"Waktu total: {end_time - start_time:.2f} detik")
    
    # Verifikasi hasil dengan memanggil /stats
    print("\nMengambil /stats untuk verifikasi...")
    try:
        # Gunakan client biasa untuk satu permintaan GET
        response = httpx.get(f"{BASE_URL}/stats")
        stats = response.json()
        
        print(f"Stats Runtime (in-memory):")
        print(f"  Total Diterima: {stats['runtime_stats (in-memory)']['total_events_received']}")
        print(f"  Total Duplikat Dibuang: {stats['runtime_stats (in-memory)']['total_duplicate_events_dropped']}")
        
        print(f"Stats Persisten (dari DB):")
        print(f"  Total Unik Diproses: {stats['persistent_stats (from_db)']['total_unique_events_processed']}")

        # Verifikasi
        assert stats['runtime_stats (in-memory)']['total_events_received'] == TOTAL_EVENTS
        assert stats['persistent_stats (from_db)']['total_unique_events_processed'] == num_unique_events
        print("\nVERIFIKASI SUKSES! ✅")
        
    except Exception as e:
        print(f"\nVERIFIKASI GAGAL ❌: {e}")

if __name__ == "__main__":
    asyncio.run(main())