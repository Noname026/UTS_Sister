import sqlite3
import logging
from pydantic import BaseModel, Field
from typing import Dict, Any
import os  # <-- Perbaikan 1: Pastikan ini ada

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Perbaikan 2: Lokasi file database dipindah ke subfolder 'data' ---
DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "aggregator.db")

# 1. Definisikan model event
class Event(BaseModel):
    topic: str
    event_id: str = Field(..., description="ID unik untuk event")
    timestamp: str  # ISO8601
    source: str
    payload: Dict[str, Any]

def init_db():
    """Membuat tabel jika belum ada."""
    
    # --- Perbaikan 3: Buat folder 'data' jika belum ada ---
    os.makedirs(DB_DIR, exist_ok=True)
            
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Tabel pelacak (kunci deduplikasi)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_ids (
            topic TEXT NOT NULL,
            event_id TEXT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (topic, event_id)
        )
        """)
        
        # Tabel data event lengkap
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            topic TEXT,
            event_id TEXT,
            timestamp TEXT,
            source TEXT,
            payload TEXT 
        )
        """)
        conn.commit()
    logger.info(f"Database berhasil diinisialisasi di {DB_FILE}")

def process_event(event: Event) -> bool:
    """
    Mencoba memproses event. 
    Mengembalikan True jika event baru (diproses).
    Mengembalikan False jika event duplikat (dilewati).
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # 1. Coba masukkan ID ke tabel pelacak
            cursor.execute(
                "INSERT INTO processed_ids (topic, event_id) VALUES (?, ?)",
                (event.topic, event.event_id)
            )
            
            # 2. Jika berhasil (baru), simpan data lengkapnya
            cursor.execute(
                "INSERT INTO events (topic, event_id, timestamp, source, payload) VALUES (?, ?, ?, ?, ?)",
                (event.topic, event.event_id, event.timestamp, event.source, str(event.payload))
            )
            
            conn.commit()
            logger.info(f"[BARU] Event diproses: {event.event_id}")
            return True
            
    except sqlite3.IntegrityError:
        # 3. Jika GAGAL (duplikat)
        logger.warning(f"[DUPLIKAT] Event dilewati: {event.event_id}")
        return False
    except Exception as e:
        # Menangani error tak terduga lainnya
        logger.error(f"Error processing event {event.event_id}: {e}")
        return False

def get_events_by_topic(topic: str) -> list:
    """Mengambil semua event unik berdasarkan topic."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE topic = ?", (topic,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_db_stats() -> dict:
    """Mengambil statistik langsung dari database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM processed_ids")
        unique_processed = cursor.fetchone()[0]
        
        cursor.execute("SELECT DISTINCT topic FROM events")
        topics = [row[0] for row in cursor.fetchall()]
        
        return {
            "unique_processed": unique_processed,
            "topics": topics
        }