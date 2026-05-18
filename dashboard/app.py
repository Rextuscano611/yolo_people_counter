import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, jsonify, Response
from analytics.aggregator import (
    get_hourly_footfall, get_peak_hours, get_today_summary,
    get_weekly_summary, get_monthly_summary, get_busiest_days
)
import cv2
import threading
import time

app = Flask(__name__)

MAX_CAPACITY = 200

# ── Shared frame buffer ───────────────────────────────────────────────────────
frame_buffer = {"frame": None, "lock": threading.Lock()}

def set_frame(frame):
    with frame_buffer["lock"]:
        frame_buffer["frame"] = frame.copy()

def generate_frames():
    while True:
        with frame_buffer["lock"]:
            frame = frame_buffer["frame"]
        if frame is None:
            time.sleep(0.01)
            continue
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Society Store — People Counter</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #0b1120;
            color: #e2e8f0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* ── Header ── */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 20px;
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            flex-shrink: 0;
        }
        .header h1 { font-size: 16px; color: #38bdf8; font-weight: 600; }
        .store-badge {
            font-size: 11px; color: #64748b;
            background: #1e293b; padding: 4px 12px; border-radius: 20px;
        }

        /* ── Tabs ── */
        .tabs {
            display: flex;
            gap: 2px;
            padding: 8px 20px 0;
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            flex-shrink: 0;
        }
        .tab {
            padding: 7px 22px;
            font-size: 12px; font-weight: 500;
            color: #64748b; cursor: pointer;
            border-radius: 6px 6px 0 0;
            border: 1px solid transparent;
            border-bottom: none;
            transition: all 0.15s;
        }
        .tab:hover { color: #e2e8f0; background: #1e293b; }
        .tab.active { color: #38bdf8; background: #0b1120; border-color: #1e293b; }

        /* ── Tab panels ── */
        .tab-content { display: none; flex: 1; overflow: hidden; }
        .tab-content.active { display: flex; }

        /* ── Shared layout pieces ── */
        .section-title {
            font-size: 11px; font-weight: 700;
            color: #64748b; text-transform: uppercase;
            letter-spacing: 0.08em; flex-shrink: 0;
        }
        .stat-card {
            background: #1e293b; border-radius: 10px;
            padding: 12px 14px; flex-shrink: 0;
        }
        .stat-card .lbl { font-size: 11px; color: #64748b; margin-bottom: 4px; }
        .stat-card .val { font-size: 28px; font-weight: 600; line-height: 1.1; }

        .peak-box {
            background: #1e293b; border-radius: 10px;
            padding: 12px 14px; flex: 1; min-height: 80px;
        }
        .peak-box .lbl { font-size: 11px; color: #64748b; margin-bottom: 8px; }
        .peak-row {
            display: flex; justify-content: space-between; align-items: center;
            padding: 6px 8px; background: #0f172a; border-radius: 6px;
            margin-bottom: 6px;
        }
        .peak-row .hr  { font-size: 12px; color: #cbd5e1; }
        .peak-row .vis { font-size: 12px; font-weight: 600; color: #38bdf8; }

        /* chart card — KEY FIX: explicit min-height so Chart.js has space */
        .chart-card {
            background: #1e293b; border-radius: 10px;
            padding: 14px 16px;
            display: flex; flex-direction: column;
        }
        .chart-card .ct { font-size: 12px; color: #94a3b8; margin-bottom: 10px; flex-shrink:0; }
        /* canvas wrapper controls the chart height */
        .chart-wrap { position: relative; height: 180px; width: 100%; }

        /* colors */
        .c-in  { color: #4ade80; }
        .c-out { color: #f87171; }
        .c-occ { color: #facc15; }
        .c-blu { color: #38bdf8; }

        /* ══ TAB 1 — LIVE ══ */
        .live-layout {
            display: flex; gap: 12px;
            padding: 12px; flex: 1; overflow: hidden;
        }
        .live-left {
            flex: 7; display: flex; flex-direction: column; gap: 10px;
        }
        .camera-box {
            flex: 1; background: #000;
            border-radius: 12px; border: 1px solid #1e293b;
            position: relative; overflow: hidden; min-height: 0;
        }
        .camera-box img { width:100%; height:100%; object-fit:contain; display:block; }
        .badge-live {
            position:absolute; top:10px; left:10px;
            background:#e24b4a; color:#fff;
            font-size:11px; padding:3px 8px; border-radius:4px;
        }
        .badge-cam {
            position:absolute; top:10px; right:10px;
            background:rgba(0,0,0,0.6); color:#ccc;
            font-size:11px; padding:3px 8px; border-radius:4px;
        }
        .counter-overlay {
            position:absolute; bottom:10px; left:10px;
            background:rgba(0,0,0,0.75); border-radius:8px;
            padding:8px 14px; display:flex; gap:16px;
        }
        .counter-overlay span { font-size:13px; font-weight:500; }

        .gauge-box {
            background:#1e293b; border-radius:10px;
            padding:10px 14px; flex-shrink:0;
        }
        .gauge-label {
            display:flex; justify-content:space-between;
            font-size:11px; color:#64748b; margin-bottom:6px;
        }
        .gauge-bar { height:10px; background:#0f172a; border-radius:6px; overflow:hidden; }
        .gauge-fill { height:100%; border-radius:6px; transition: width 0.5s ease, background 0.5s ease; }

        .live-right {
            flex: 3; display: flex; flex-direction: column;
            gap: 10px; overflow-y: auto; min-width: 0;
        }

        /* ══ TAB 2 — TODAY ══ */
        .today-layout {
            display: flex; gap: 12px;
            padding: 12px; flex: 1; overflow: hidden;
        }
        .today-left {
            flex: 7; display: flex; flex-direction: column; gap: 10px; min-height: 0;
        }
        .today-right {
            flex: 3; display: flex; flex-direction: column;
            gap: 10px; overflow-y: auto; min-width: 0;
        }
        .summary-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 10px; flex-shrink: 0;
        }

        /* ══ TAB 3 — HISTORY ══ */
        .history-layout {
            display: flex; gap: 12px;
            padding: 12px; flex: 1; overflow: hidden;
        }
        .history-left {
            flex: 6; display: flex; flex-direction: column;
            gap: 10px; overflow-y: auto; min-width: 0;
        }
        .history-right {
            flex: 4; display: flex; flex-direction: column;
            gap: 10px; overflow-y: auto; min-width: 0;
        }
        .summary-banner {
            background: #1e293b; border-radius: 10px;
            padding: 12px 14px; flex-shrink: 0;
        }
        .banner-row { display: flex; gap: 0; }
        .banner-cell { flex: 1; padding: 0 12px; }
        .banner-cell:first-child { padding-left: 0; }
        .banner-cell:not(:last-child) { border-right: 1px solid #334155; }
        .banner-cell .bp { font-size: 11px; color: #64748b; margin-bottom: 3px; }
        .banner-cell .bv { font-size: 24px; font-weight: 600; }
    </style>
</head>
<body>

<div class="header">
    <h1>🛒 Society Stores — People Counter</h1>
    <span class="store-badge" id="clock">--:--:--</span>
</div>

<div class="tabs">
    <div class="tab active" onclick="switchTab('live')">📷 Live</div>
    <div class="tab"        onclick="switchTab('today')">📊 Today</div>
    <div class="tab"        onclick="switchTab('history')">📅 History</div>
</div>

<!-- ══ TAB 1: LIVE ══ -->
<div class="tab-content active" id="tab-live">
    <div class="live-layout">
        <div class="live-left">
            <div class="camera-box">
                <img src="/video_feed" alt="Live feed" />
                <div class="badge-live">● LIVE</div>
                <div class="badge-cam">CAM 01 — Entry</div>
                <div class="counter-overlay">
                    <span class="c-in"  id="ov-in">IN: —</span>
                    <span class="c-out" id="ov-out">OUT: —</span>
                    <span class="c-occ" id="ov-occ">OCC: —</span>
                </div>
            </div>
            <div class="gauge-box">
                <div class="gauge-label">
                    <span>Store occupancy</span>
                    <span id="gauge-text">— / {{ max_capacity }}</span>
                </div>
                <div class="gauge-bar">
                    <div class="gauge-fill" id="gauge-fill" style="width:0%"></div>
                </div>
            </div>
        </div>
        <div class="live-right">
            <p class="section-title">Live stats</p>
            <div class="stat-card">
                <div class="lbl">Total in (today)</div>
                <div class="val c-in" id="live-total-in">—</div>
            </div>
            <div class="stat-card">
                <div class="lbl">Total out (today)</div>
                <div class="val c-out" id="live-total-out">—</div>
            </div>
            <div class="stat-card">
                <div class="lbl">Current occupancy</div>
                <div class="val c-occ" id="live-occupancy">—</div>
            </div>
            <div class="stat-card">
                <div class="lbl">Peak occupancy</div>
                <div class="val c-blu" id="live-peak">—</div>
            </div>
            <div class="peak-box">
                <div class="lbl">Top peak hours today</div>
                <div id="live-peak-list"></div>
            </div>
        </div>
    </div>
</div>

<!-- ══ TAB 2: TODAY ══ -->
<div class="tab-content" id="tab-today">
    <div class="today-layout">
        <div class="today-left">
            <!-- chart-wrap gives Chart.js a real height to work with -->
            <div class="chart-card" style="flex:1; min-height:0;">
                <div class="ct">Hourly footfall — today</div>
                <div class="chart-wrap" style="flex:1; height:auto;">
                    <canvas id="hourlyChart"></canvas>
                </div>
            </div>
        </div>
        <div class="today-right">
            <p class="section-title">Today's summary</p>
            <div class="summary-grid">
                <div class="stat-card">
                    <div class="lbl">Total in</div>
                    <div class="val c-in" id="today-in">—</div>
                </div>
                <div class="stat-card">
                    <div class="lbl">Total out</div>
                    <div class="val c-out" id="today-out">—</div>
                </div>
                <div class="stat-card">
                    <div class="lbl">Occupancy now</div>
                    <div class="val c-occ" id="today-occ">—</div>
                </div>
                <div class="stat-card">
                    <div class="lbl">Peak occupancy</div>
                    <div class="val c-blu" id="today-peak">—</div>
                </div>
            </div>
            <div class="peak-box">
                <div class="lbl">Top peak hours</div>
                <div id="today-peak-list"></div>
            </div>
        </div>
    </div>
</div>

<!-- ══ TAB 3: HISTORY ══ -->
<div class="tab-content" id="tab-history">
    <div class="history-layout">
        <div class="history-left">
            <div class="chart-card">
                <div class="ct">Last 7 days — daily visitors</div>
                <div class="chart-wrap"><canvas id="weeklyChart"></canvas></div>
            </div>
            <div class="chart-card">
                <div class="ct">This month — daily visitors</div>
                <div class="chart-wrap"><canvas id="monthlyChart"></canvas></div>
            </div>
            <div class="chart-card">
                <div class="ct">Average visitors by day of week</div>
                <div class="chart-wrap"><canvas id="dowChart"></canvas></div>
            </div>
        </div>
        <div class="history-right">
            <p class="section-title">Weekly summary</p>
            <div class="summary-banner">
                <div class="banner-row">
                    <div class="banner-cell">
                        <div class="bp">Last 7 days — IN</div>
                        <div class="bv c-in" id="week-in">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">Last 7 days — OUT</div>
                        <div class="bv c-out" id="week-out">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">Peak occupancy</div>
                        <div class="bv c-blu" id="week-peak">—</div>
                    </div>
                </div>
            </div>

            <p class="section-title">Monthly summary</p>
            <div class="summary-banner">
                <div class="banner-row">
                    <div class="banner-cell">
                        <div class="bp" id="month-label">This month — IN</div>
                        <div class="bv c-in" id="month-in">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">This month — OUT</div>
                        <div class="bv c-out" id="month-out">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">Peak occupancy</div>
                        <div class="bv c-blu" id="month-peak">—</div>
                    </div>
                </div>
            </div>

            <p class="section-title">Busiest days</p>
            <div class="peak-box" style="flex:1;">
                <div class="lbl">Average visitors per day of week (all time)</div>
                <div id="dow-list"></div>
            </div>
        </div>
    </div>
</div>

<script>
const MAX_CAP = {{ max_capacity }};
let charts = {};
let activeTab = 'live';

// ── Clock ──────────────────────────────────────────────────────────────────
function tick() { document.getElementById('clock').textContent = new Date().toLocaleTimeString(); }
setInterval(tick, 1000); tick();

// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(name) {
    activeTab = name;
    document.querySelectorAll('.tab').forEach((t, i) => {
        t.classList.toggle('active', ['live','today','history'][i] === name);
    });
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    // Small delay so DOM is visible before Chart.js measures canvas
    setTimeout(fetchAll, 20);
}

// ── Chart helpers ──────────────────────────────────────────────────────────
function makeOrUpdate(id, type, labels, datasets) {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    if (charts[id]) {
        charts[id].data.labels   = labels;
        charts[id].data.datasets = datasets;
        charts[id].update();
        return;
    }
    charts[id] = new Chart(ctx, {
        type,
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color:'#94a3b8', boxWidth:12, font:{size:11} } }
            },
            scales: {
                x: { ticks:{color:'#64748b', font:{size:10}}, grid:{color:'#1e293b'} },
                y: { ticks:{color:'#64748b', font:{size:10}}, grid:{color:'#334155'}, beginAtZero:true }
            }
        }
    });
}

// ── Gauge ──────────────────────────────────────────────────────────────────
function updateGauge(occ) {
    const pct  = Math.min(100, Math.round(occ / MAX_CAP * 100));
    const fill = document.getElementById('gauge-fill');
    fill.style.width      = pct + '%';
    fill.style.background = pct < 60 ? '#4ade80' : pct < 85 ? '#facc15' : '#f87171';
    document.getElementById('gauge-text').textContent = occ + ' / ' + MAX_CAP;
}

// ── Fetch: LIVE ────────────────────────────────────────────────────────────
async function fetchLive() {
    const s   = await fetch('/api/summary').then(r => r.json());
    const occ = Math.max(0, s.total_in - s.total_out);
    document.getElementById('live-total-in').textContent  = s.total_in;
    document.getElementById('live-total-out').textContent = s.total_out;
    document.getElementById('live-occupancy').textContent = occ;
    document.getElementById('live-peak').textContent      = s.peak_occupancy;
    document.getElementById('ov-in').textContent          = 'IN: '  + s.total_in;
    document.getElementById('ov-out').textContent         = 'OUT: ' + s.total_out;
    document.getElementById('ov-occ').textContent         = 'OCC: ' + occ;
    updateGauge(occ);

    const p = await fetch('/api/peaks').then(r => r.json());
    document.getElementById('live-peak-list').innerHTML = p.length
        ? p.map((r,i) => `<div class="peak-row">
              <span class="hr">#${i+1} &nbsp; ${r.hour.split(' ')[1]}:00</span>
              <span class="vis">${r.count_in} visitors</span>
            </div>`).join('')
        : '<div style="color:#475569;font-size:12px;padding:6px">No data yet</div>';
}

// ── Fetch: TODAY ───────────────────────────────────────────────────────────
async function fetchToday() {
    const s   = await fetch('/api/summary').then(r => r.json());
    const occ = Math.max(0, s.total_in - s.total_out);
    document.getElementById('today-in').textContent   = s.total_in;
    document.getElementById('today-out').textContent  = s.total_out;
    document.getElementById('today-occ').textContent  = occ;
    document.getElementById('today-peak').textContent = s.peak_occupancy;

    const h = await fetch('/api/hourly').then(r => r.json());
    makeOrUpdate('hourlyChart', 'bar',
        h.map(r => r.hour.split(' ')[1] + ':00'),
        [
            { label:'IN',  data:h.map(r=>r.count_in),  backgroundColor:'rgba(74,222,128,0.75)' },
            { label:'OUT', data:h.map(r=>r.count_out), backgroundColor:'rgba(248,113,113,0.75)' }
        ]
    );

    const p = await fetch('/api/peaks').then(r => r.json());
    document.getElementById('today-peak-list').innerHTML = p.length
        ? p.map((r,i) => `<div class="peak-row">
              <span class="hr">#${i+1} &nbsp; ${r.hour.split(' ')[1]}:00</span>
              <span class="vis">${r.count_in} visitors</span>
            </div>`).join('')
        : '<div style="color:#475569;font-size:12px;padding:6px">No data yet</div>';
}

// ── Fetch: HISTORY ─────────────────────────────────────────────────────────
async function fetchHistory() {
    // Weekly
    const w = await fetch('/api/weekly').then(r => r.json());
    document.getElementById('week-in').textContent   = w.total_in;
    document.getElementById('week-out').textContent  = w.total_out;
    document.getElementById('week-peak').textContent = w.peak_occupancy;
    makeOrUpdate('weeklyChart', 'bar',
        w.daily.map(d => d.label),
        [
            { label:'IN',  data:w.daily.map(d=>d.count_in),  backgroundColor:'rgba(74,222,128,0.75)' },
            { label:'OUT', data:w.daily.map(d=>d.count_out), backgroundColor:'rgba(248,113,113,0.75)' }
        ]
    );

    // Monthly
    const m = await fetch('/api/monthly').then(r => r.json());
    document.getElementById('month-label').textContent = m.month_label + ' — IN';
    document.getElementById('month-in').textContent    = m.total_in;
    document.getElementById('month-out').textContent   = m.total_out;
    document.getElementById('month-peak').textContent  = m.peak_occupancy;
    makeOrUpdate('monthlyChart', 'bar',
        m.daily.map(d => d.label),
        [
            { label:'IN', data:m.daily.map(d=>d.count_in), backgroundColor:'rgba(56,189,248,0.75)' }
        ]
    );

    // Day of week
    const d = await fetch('/api/busiest_days').then(r => r.json());
    makeOrUpdate('dowChart', 'bar',
        d.map(x => x.day),
        [
            { label:'Avg visitors', data:d.map(x=>x.avg_visitors), backgroundColor:'rgba(250,204,21,0.75)' }
        ]
    );

    const sorted = [...d].sort((a,b) => b.avg_visitors - a.avg_visitors);
    document.getElementById('dow-list').innerHTML = sorted.some(x => x.avg_visitors > 0)
        ? sorted.map((x,i) => `<div class="peak-row">
              <span class="hr">#${i+1} &nbsp; ${x.day}</span>
              <span class="vis">${x.avg_visitors} avg</span>
            </div>`).join('')
        : '<div style="color:#475569;font-size:12px;padding:6px">Not enough data yet — run for a few days</div>';
}

// ── Main ───────────────────────────────────────────────────────────────────
async function fetchAll() {
    try {
        if (activeTab === 'live')    await fetchLive();
        if (activeTab === 'today')   await fetchToday();
        if (activeTab === 'history') await fetchHistory();
    } catch(e) { console.error('Fetch error:', e); }
}

fetchAll();
setInterval(fetchAll, 10000);
</script>
</body>
</html>
"""

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML, max_capacity=MAX_CAPACITY)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/summary')
def api_summary():    return jsonify(get_today_summary())

@app.route('/api/hourly')
def api_hourly():     return jsonify(get_hourly_footfall())

@app.route('/api/peaks')
def api_peaks():      return jsonify(get_peak_hours())

@app.route('/api/weekly')
def api_weekly():     return jsonify(get_weekly_summary())

@app.route('/api/monthly')
def api_monthly():    return jsonify(get_monthly_summary())

@app.route('/api/busiest_days')
def api_busiest():    return jsonify(get_busiest_days())


if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True)