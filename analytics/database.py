import sqlite3
import os
from datetime import datetime
from config.settings import DB_PATH


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Stores every IN/OUT event with timestamp
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,        -- 'IN' or 'OUT'
            track_id    INTEGER NOT NULL,
            timestamp   TEXT NOT NULL
        )
    """)

    # Stores hourly aggregated footfall
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hourly_footfall (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            hour         TEXT NOT NULL UNIQUE, -- '2024-01-15 09'
            count_in     INTEGER DEFAULT 0,
            count_out    INTEGER DEFAULT 0,
            peak_ocupancy INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Initialised at:", DB_PATH)


def log_event(event_type, track_id):
    """Log a single IN or OUT event."""
    conn = get_connection()
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO events (event_type, track_id, timestamp)
        VALUES (?, ?, ?)
    """, (event_type, track_id, timestamp))

    conn.commit()
    conn.close()


def update_hourly(count_in, count_out, occupancy):
    """Upsert hourly footfall record for current hour."""
    conn = get_connection()
    cursor = conn.cursor()

    hour = datetime.now().strftime("%Y-%m-%d %H")

    cursor.execute("""
        INSERT INTO hourly_footfall (hour, count_in, count_out, peak_ocupancy)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(hour) DO UPDATE SET
            count_in      = excluded.count_in,
            count_out     = excluded.count_out,
            peak_ocupancy = MAX(peak_ocupancy, excluded.peak_ocupancy)
    """, (hour, count_in, count_out, occupancy))

    conn.commit()
    conn.close()