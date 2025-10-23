import time
from fastapi import FastAPI, HTTPException, Body
from typing import List, Union, Dict, Any
from contextlib import asynccontextmanager  # <-- Diperlukan untuk lifespan
from . import database
from .database import Event

# Variabel global (in-memory)
STATS = {
    "received": 0,
    "duplicate_dropped": 0
}
START_TIME = time.time()


# --- Lifespan Event Handler (Pengganti on_startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dijalankan saat startup
    database.init_db()
    print("Startup complete. Database initialized.")
    yield
    # Dijalankan saat shutdown
    print("Shutdown complete.")


# --- Aplikasi FastAPI (Menggunakan lifespan) ---
app = FastAPI(title="UTS Log Aggregator", lifespan=lifespan)


# a. Endpoint POST /publish
@app.post("/publish")
async def publish_events(events: Union[Event, List[Event]]):
    """
    Menerima satu atau batch event.
    Endpoint ini akan memanggil 'process_event' yang idempotent.
    """
    if not isinstance(events, list):
        events = [events] # Ubah event tunggal menjadi list agar mudah di-loop

    processed_count = 0
    dropped_count = 0

    for event in events:
        STATS["received"] += 1
        is_new = database.process_event(event) # Panggil fungsi inti kita
        if is_new:
            processed_count += 1
        else:
            dropped_count += 1
            STATS["duplicate_dropped"] += 1
            
    return {
        "message": "Events processed",
        "total_received_in_batch": len(events),
        "newly_processed": processed_count,
        "duplicates_dropped_in_batch": dropped_count
    }

# b. Endpoint GET /events
@app.get("/events")
async def get_events(topic: str):
    """Mengembalikan daftar event unik yang telah diproses untuk suatu topik."""
    events = database.get_events_by_topic(topic)
    return {
        "topic": topic,
        "count": len(events),
        "events": events
    }

# c. Endpoint GET /stats
@app.get("/stats")
async def get_statistics():
    """Menampilkan statistik sistem."""
    
    # Ambil stats dari DB (yang persisten)
    db_stats = database.get_db_stats()
    
    # Gabungkan dengan stats in-memory
    uptime_seconds = time.time() - START_TIME
    
    return {
        "uptime_seconds": round(uptime_seconds, 2),
        "runtime_stats (in-memory)": {
            "total_events_received": STATS["received"],
            "total_duplicate_events_dropped": STATS["duplicate_dropped"],
        },
        "persistent_stats (from_db)": {
            "total_unique_events_processed": db_stats["unique_processed"],
            "known_topics": db_stats["topics"]
        }
    }