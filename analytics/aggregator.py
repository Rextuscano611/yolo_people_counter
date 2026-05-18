import sqlite3
from datetime import datetime, timedelta
from analytics.database import get_connection


def get_hourly_footfall():
    """Returns hourly footfall records for today only."""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT hour, count_in, count_out, peak_ocupancy
        FROM hourly_footfall
        WHERE hour LIKE ?
        ORDER BY hour ASC
    """, (f"{today}%",))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "hour":           row[0],
            "count_in":       row[1],
            "count_out":      row[2],
            "peak_occupancy": row[3]
        }
        for row in rows
    ]


def get_peak_hours():
    """Returns top 3 busiest hours by IN count for today."""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT hour, count_in
        FROM hourly_footfall
        WHERE hour LIKE ?
        ORDER BY count_in DESC
        LIMIT 3
    """, (f"{today}%",))
    rows = cursor.fetchall()
    conn.close()
    return [{"hour": row[0], "count_in": row[1]} for row in rows]


def get_today_summary():
    """Returns total IN, OUT and peak occupancy for today."""
    conn = get_connection()
    cursor = conn.cursor()
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


def get_weekly_summary():
    """
    Returns total IN, OUT and peak occupancy for the current week (Mon–today).
    Also returns daily breakdown for the 7-day trend chart.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Last 7 days including today
    today = datetime.now().date()
    days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    daily = []
    total_in = 0
    total_out = 0
    peak_occ = 0

    for day in days:
        cursor.execute("""
            SELECT
                COALESCE(SUM(count_in), 0),
                COALESCE(SUM(count_out), 0),
                COALESCE(MAX(peak_ocupancy), 0)
            FROM hourly_footfall
            WHERE hour LIKE ?
        """, (f"{day}%",))
        row = cursor.fetchone()
        day_in, day_out, day_peak = row[0], row[1], row[2]

        daily.append({
            "date":     day,
            "label":    datetime.strptime(day, "%Y-%m-%d").strftime("%a %d"),
            "count_in":  day_in,
            "count_out": day_out,
            "peak_occupancy": day_peak
        })

        total_in  += day_in
        total_out += day_out
        peak_occ   = max(peak_occ, day_peak)

    conn.close()
    return {
        "total_in":       total_in,
        "total_out":      total_out,
        "peak_occupancy": peak_occ,
        "daily":          daily
    }


def get_monthly_summary():
    """
    Returns total IN, OUT and peak occupancy for the current month.
    Also returns daily breakdown for each day of the current month.
    """
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date()
    year_month = today.strftime("%Y-%m")

    # All days from 1st of month to today
    days = []
    day = today.replace(day=1)
    while day <= today:
        days.append(day.strftime("%Y-%m-%d"))
        day += timedelta(days=1)

    daily = []
    total_in = 0
    total_out = 0
    peak_occ = 0

    for d in days:
        cursor.execute("""
            SELECT
                COALESCE(SUM(count_in), 0),
                COALESCE(SUM(count_out), 0),
                COALESCE(MAX(peak_ocupancy), 0)
            FROM hourly_footfall
            WHERE hour LIKE ?
        """, (f"{d}%",))
        row = cursor.fetchone()
        day_in, day_out, day_peak = row[0], row[1], row[2]

        daily.append({
            "date":           d,
            "label":          datetime.strptime(d, "%Y-%m-%d").strftime("%d"),
            "count_in":       day_in,
            "count_out":      day_out,
            "peak_occupancy": day_peak
        })

        total_in  += day_in
        total_out += day_out
        peak_occ   = max(peak_occ, day_peak)

    conn.close()
    return {
        "total_in":       total_in,
        "total_out":      total_out,
        "peak_occupancy": peak_occ,
        "month_label":    today.strftime("%B %Y"),
        "daily":          daily
    }


def get_busiest_days():
    """
    Returns average visitors per day of week (Mon–Sun) across all recorded data.
    Useful for staff scheduling — shows which days are historically busiest.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # SQLite strftime %w: 0=Sunday, 1=Monday ... 6=Saturday
    cursor.execute("""
        SELECT
            CAST(strftime('%w', hour) AS INTEGER) AS dow,
            COALESCE(SUM(count_in), 0)            AS total_in,
            COUNT(DISTINCT substr(hour, 1, 10))    AS num_days
        FROM hourly_footfall
        GROUP BY dow
        ORDER BY dow ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    result = {name: 0 for name in day_names}
    for row in rows:
        dow, total_in, num_days = row
        avg = round(total_in / num_days) if num_days > 0 else 0
        result[day_names[dow]] = avg

    # Return in Mon–Sun order for the chart
    ordered = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return [{"day": d, "avg_visitors": result[d]} for d in ordered]