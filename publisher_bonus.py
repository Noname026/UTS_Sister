import httpx
import time
import sys

# PENTING:
# Saat berjalan di Docker Compose, service 'aggregator' bisa diakses
# menggunakan nama service-nya, BUKAN 'localhost'.
AGGREGATOR_URL = "http://aggregator:8080/publish"

def main():
    print("[Publisher]: Memulai...")

    # Beri waktu 5 detik agar service aggregator (database) siap
    print("[Publisher]: Menunggu aggregator siap... (5 detik)")
    time.sleep(5)

    event1 = {
        "topic": "bonus-test", "event_id": "bonus-001", "timestamp": "2025-10-24T10:00:00Z",
        "source": "publisher-service", "payload": {"data": "A"}
    }
    event2 = {
        "topic": "bonus-test", "event_id": "bonus-002", "timestamp": "2025-10-24T10:01:00Z",
        "source": "publisher-service", "payload": {"data": "B"}
    }
    event3_dup = event1  # Ini adalah duplikat dari event 1

    events_to_send = [event1, event2, event3_dup]

    try:
        with httpx.Client() as client:
            for event in events_to_send:
                print(f"[Publisher]: Mengirim event_id: {event['event_id']}")
                response = client.post(AGGREGATOR_URL, json=event, timeout=10)
                response.raise_for_status() # Error jika status bukan 2xx
                print(f"[Publisher]: ...Sukses (Response: {response.json()})")
                time.sleep(1) # Beri jeda 1 detik

    except httpx.RequestError as e:
        print(f"[Publisher]: GAGAL KONEKSI. Apakah 'aggregator' sudah jalan?", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[Publisher]: Error tak terduga: {e}", file=sys.stderr)
        sys.exit(1)

    print("[Publisher]: Selesai mengirim 3 event (1 duplikat). Keluar.")

if __name__ == "__main__":
    main()