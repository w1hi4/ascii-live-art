import os
import zlib
import time
import sqlite3
import threading
import tempfile
from collections import OrderedDict

# Default DB location in temp or local dir
DB_PATH = os.path.join(tempfile.gettempdir(), "ascii_live_database.db")

class LRUCache:
    """Thread-safe in-memory LRU cache for the hottest animations."""
    def __init__(self, capacity=500):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]

    def put(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

# Global in-memory cache and view buffer
FRAME_CACHE = LRUCache(capacity=500)
VIEW_BUFFER = {}
VIEW_LOCK = threading.Lock()
DB_LOCK = threading.Lock()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -32000;") # 32MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables and high-performance indexes."""
    with DB_LOCK:
        conn = get_db_connection()
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS animations (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                fps INTEGER DEFAULT 12,
                width INTEGER DEFAULT 54,
                mode TEXT DEFAULT 'halfblock',
                effect TEXT DEFAULT 'scanner',
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                created_at REAL,
                frames_blob BLOB NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anim_views ON animations(views DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_anim_created ON animations(created_at DESC);")
            conn.commit()
        finally:
            conn.close()

def save_animation(slug, title, fps, width, mode, effect, frames):
    """
    Compresses frames using zlib and saves to SQLite.
    Also updates in-memory LRU cache.
    """
    slug = slug.strip("/").lower()
    raw_payload = "\n---FRAME---\n".join(frames).encode("utf-8")
    compressed = zlib.compress(raw_payload, level=6)

    data_record = {
        "slug": slug,
        "title": title,
        "fps": fps,
        "width": width,
        "mode": mode,
        "effect": effect,
        "frames": frames,
        "created_at": time.time(),
        "views": 0,
        "likes": 0,
    }

    # Cache immediately
    FRAME_CACHE.put(slug, data_record)

    with DB_LOCK:
        conn = get_db_connection()
        try:
            conn.execute("""
            INSERT INTO animations (slug, title, fps, width, mode, effect, views, likes, created_at, frames_blob)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title = excluded.title,
                fps = excluded.fps,
                width = excluded.width,
                mode = excluded.mode,
                effect = excluded.effect,
                frames_blob = excluded.frames_blob;
            """, (slug, title, fps, width, mode, effect, time.time(), compressed))
            conn.commit()
        finally:
            conn.close()

    return data_record

def get_animation(slug):
    """
    Retrieves animation from LRU cache or decompresses from SQLite.
    Returns dict or None.
    """
    slug = slug.strip("/").lower()

    # 1. Check LRU Cache (0ms disk latency)
    cached = FRAME_CACHE.get(slug)
    if cached:
        return cached

    # 2. Fetch from SQLite
    with DB_LOCK:
        conn = get_db_connection()
        try:
            cur = conn.execute("SELECT * FROM animations WHERE slug = ?", (slug,))
            row = cur.fetchone()
            if not row:
                return None

            # Decompress frames
            raw = zlib.decompress(row["frames_blob"]).decode("utf-8")
            frames = raw.split("\n---FRAME---\n")

            data = {
                "slug": row["slug"],
                "title": row["title"],
                "fps": row["fps"],
                "width": row["width"],
                "mode": row["mode"],
                "effect": row["effect"],
                "views": row["views"],
                "likes": row["likes"],
                "created_at": row["created_at"],
                "frames": frames,
            }
            FRAME_CACHE.put(slug, data)
            return data
        finally:
            conn.close()

def list_animations(limit=50, offset=0, search=None, sort_by="views"):
    """
    Returns list of animations with metadata and view counts.
    """
    with DB_LOCK:
        conn = get_db_connection()
        try:
            query = "SELECT slug, title, fps, width, mode, effect, views, likes, created_at FROM animations"
            params = []

            if search:
                query += " WHERE slug LIKE ? OR title LIKE ?"
                s = f"%{search}%"
                params.extend([s, s])

            if sort_by == "newest":
                query += " ORDER BY created_at DESC"
            else:
                query += " ORDER BY views DESC, created_at DESC"

            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cur = conn.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

def record_view(slug):
    """Buffers views in-memory for zero disk-contention during high concurrency."""
    with VIEW_LOCK:
        VIEW_BUFFER[slug] = VIEW_BUFFER.get(slug, 0) + 1

def flush_views_to_db():
    """Batches buffered views to SQLite."""
    with VIEW_LOCK:
        if not VIEW_BUFFER:
            return
        to_flush = dict(VIEW_BUFFER)
        VIEW_BUFFER.clear()

    with DB_LOCK:
        conn = get_db_connection()
        try:
            for slug, count in to_flush.items():
                conn.execute("UPDATE animations SET views = views + ? WHERE slug = ?", (count, slug))
            conn.commit()
        finally:
            conn.close()

def get_stats():
    """Returns global platform stats."""
    with DB_LOCK:
        conn = get_db_connection()
        try:
            cur = conn.execute("SELECT COUNT(*) as total_count, COALESCE(SUM(views), 0) as total_views FROM animations")
            row = cur.fetchone()
            return {
                "total_animations": row["total_count"],
                "total_views": row["total_views"],
            }
        finally:
            conn.close()

# Auto-initialize DB on import
init_db()

