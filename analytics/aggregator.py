import sqlite3
from analytics.database import get_connection


def get_hourly_footfall():
    """Returns all hourly footfall records."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT hour, count_in, count_out, peak_ocupancy
        FROM hourly_footfall
        ORDER BY hour ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "hour":          row[0],
            "count_in":      row[1],
            "count_out":     row[2],
            "peak_occupancy": row[3]
        }
        for row in rows
    ]


def get_peak_hours():
    """Returns top 3 busiest hours by IN count."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT hour, count_in
        FROM hourly_footfall
        ORDER BY count_in DESC
        LIMIT 3
    """)

    rows = cursor.fetchall()
    conn.close()

    return [{"hour": row[0], "count_in": row[1]} for row in rows]


def get_today_summary():
    """Returns total IN, OUT and peak occupancy for today."""
    conn = get_connection()
    cursor = conn.cursor()

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT 
            SUM(count_in),
            SUM(count_out),
            MAX(peak_ocupancy)
        FROM hourly_footfall
        WHERE hour LIKE ?
    """, (f"{today}%",))

    row = cursor.fetchone()
    conn.close()

    return {
        "total_in":       row[0] or 0,
        "total_out":      row[1] or 0,
        "peak_occupancy": row[2] or 0
    }