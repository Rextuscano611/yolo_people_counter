import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, jsonify, Response
from analytics.aggregator import (
    get_hourly_footfall, get_peak_hours, get_today_summary,
    get_weekly_summary, get_monthly_summary, get_busiest_days,
    get_yearly_heatmap
)
import cv2
import threading
import time

app = Flask(__name__)
MAX_CAPACITY = 200

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

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Society Stores® — Store Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
    :root {
        --green:        #7BC242;
        --green-dark:   #4e8220;
        --green-light:  #f0f8e8;
        --orange:       #F28C18;
        --orange-light: #fff4e6;
        --bg:           #f5f4f0;
        --surface:      #ffffff;
        --surface2:     #fafaf7;
        --border:       #e4e2db;
        --border-light: #eeede8;
        --text:         #1c2b1c;
        --text-mid:     #4a5e4a;
        --text-muted:   #8a9e8a;
        --text-dim:     #b5c4b5;
        --serif: 'DM Serif Display', serif;
        --sans:  'DM Sans', sans-serif;
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
    }
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
        font-family: var(--sans);
        background: var(--bg);
        color: var(--text);
        height: 100vh;
        display: flex; flex-direction: column;
        overflow: hidden;
    }

    /* ── Header ──────────────────────────────────────── */
    .header {
        display:flex; align-items:center; justify-content:space-between;
        padding:0 24px; height:56px;
        background:#ffffff;
        border-bottom:3px solid var(--green);
        box-shadow:var(--shadow-sm);
        flex-shrink:0; z-index:10; position:relative;
    }
    .header-left { display:flex; align-items:center; gap:14px; }
    .logo-leaf { width:32px; height:32px; flex-shrink:0; }
    .logo-leaf svg { width:100%; height:100%; }
    .brand-block { display:flex; flex-direction:column; gap:1px; }
    .brand-name {
        font-family:var(--serif); font-size:19px;
        color:var(--green-dark); line-height:1; letter-spacing:0.01em;
    }
    .brand-name sup { font-size:9px; color:var(--orange); vertical-align:super; font-family:var(--sans); }
    .brand-tag {
        font-size:10px; color:var(--text-muted);
        font-style:italic; font-family:var(--serif); letter-spacing:0.03em;
    }
    .header-center {
        position:absolute; left:50%; transform:translateX(-50%);
        font-size:11px; font-weight:600; color:var(--text-mid);
        letter-spacing:0.14em; text-transform:uppercase;
    }
    .header-right { display:flex; align-items:center; gap:14px; }
    .clock { font-family:var(--serif); font-size:16px; color:var(--green-dark); letter-spacing:0.04em; }
    .est-pill {
        font-size:10px; font-weight:500; color:var(--text-muted);
        border:1px solid var(--border); background:var(--surface2);
        padding:3px 10px; border-radius:20px; letter-spacing:0.08em;
    }

    /* ── Tabs ────────────────────────────────────────── */
    .tabs {
        display:flex; padding:0 24px;
        background:var(--surface);
        border-bottom:1px solid var(--border);
        flex-shrink:0; z-index:9;
    }
    .tab {
        padding:10px 24px;
        font-size:11px; font-weight:600; color:var(--text-muted);
        cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px;
        transition:all 0.18s; letter-spacing:0.08em; text-transform:uppercase;
    }
    .tab:hover { color:var(--green-dark); }
    .tab.active { color:var(--green-dark); border-bottom-color:var(--green); }

    /* ── Panels ──────────────────────────────────────── */
    .tab-content { display:none; flex:1; overflow:hidden; }
    .tab-content.active { display:flex; }
    .panel-layout { display:flex; gap:14px; padding:14px; flex:1; overflow:hidden; }
    .left-col  { display:flex; flex-direction:column; gap:12px; min-height:0; }
    .right-col {
        display:flex; flex-direction:column;
        gap:10px; overflow-y:auto; min-width:0;
    }
    .right-col::-webkit-scrollbar { width:3px; }
    .right-col::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }

    /* ── Shared components ───────────────────────────── */
    .card {
        background:var(--surface); border:1px solid var(--border);
        border-radius:10px; padding:14px 16px;
        flex-shrink:0; box-shadow:var(--shadow-sm);
    }
    .card-label {
        font-size:10px; font-weight:600; color:var(--text-muted);
        text-transform:uppercase; letter-spacing:0.1em; margin-bottom:5px;
    }
    .card-value { font-family:var(--serif); font-size:34px; line-height:1.1; }
    .stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; flex-shrink:0; }
    .stat-grid .card-value { font-size:30px; }
    .card-in   { border-left:3px solid var(--green); }
    .card-out  { border-left:3px solid var(--orange); }
    .card-occ  { border-left:3px solid #e9b824; }
    .card-peak { border-left:3px solid var(--text-dim); }

    .section-label {
        font-size:10px; font-weight:700; color:var(--text-muted);
        text-transform:uppercase; letter-spacing:0.12em; flex-shrink:0;
        display:flex; align-items:center; gap:8px;
    }
    .section-label::after { content:''; flex:1; height:1px; background:var(--border); }

    .chart-card {
        background:var(--surface); border:1px solid var(--border);
        border-radius:10px; padding:14px 16px;
        display:flex; flex-direction:column; box-shadow:var(--shadow-sm);
    }
    .chart-title {
        font-size:10px; font-weight:600; color:var(--text-muted);
        text-transform:uppercase; letter-spacing:0.1em; margin-bottom:12px; flex-shrink:0;
    }
    .chart-wrap { position:relative; height:180px; width:100%; }

    .peak-card {
        background:var(--surface); border:1px solid var(--border);
        border-radius:10px; padding:14px 16px;
        flex:1; min-height:60px; box-shadow:var(--shadow-sm);
    }
    .peak-row {
        display:flex; justify-content:space-between; align-items:center;
        padding:7px 10px; background:var(--surface2);
        border:1px solid var(--border-light); border-radius:6px; margin-bottom:6px;
    }
    .peak-row:last-child { margin-bottom:0; }
    .peak-hr  { font-size:12px; color:var(--text); font-weight:500; }
    .peak-vis { font-size:12px; font-weight:600; color:var(--orange); }

    .c-green  { color:var(--green-dark); }
    .c-orange { color:var(--orange); }
    .c-occ    { color:#c07d00; }
    .c-muted  { color:var(--text-mid); }

    /* ── Live tab ────────────────────────────────────── */
    .camera-box {
        flex:1; min-height:0; background:#111;
        border-radius:10px; border:1px solid var(--border);
        position:relative; overflow:hidden; box-shadow:var(--shadow-md);
    }
    .camera-box img { width:100%; height:100%; object-fit:contain; display:block; }
    .cam-badge {
        position:absolute; top:10px;
        font-size:10px; font-weight:600; padding:4px 10px;
        border-radius:4px; letter-spacing:0.06em;
    }
    .badge-live { left:10px; background:#c0392b; color:#fff; }
    .badge-cam  { right:10px; background:rgba(0,0,0,0.65); color:#ccc; border:1px solid rgba(255,255,255,0.1); }
    .cam-overlay {
        position:absolute; bottom:10px; left:10px;
        background:rgba(255,255,255,0.92); border:1px solid var(--border);
        border-radius:8px; padding:7px 14px;
        display:flex; gap:18px; box-shadow:var(--shadow-sm);
    }
    .cam-overlay span { font-size:12px; font-weight:600; }
    .gauge-wrap {
        background:var(--surface); border:1px solid var(--border);
        border-radius:10px; padding:10px 14px;
        flex-shrink:0; box-shadow:var(--shadow-sm);
    }
    .gauge-labels {
        display:flex; justify-content:space-between;
        font-size:10px; color:var(--text-muted); margin-bottom:6px;
        text-transform:uppercase; letter-spacing:0.08em;
    }
    .gauge-track {
        height:8px; background:var(--bg); border-radius:4px; overflow:hidden;
        border:1px solid var(--border-light);
    }
    .gauge-fill { height:100%; border-radius:4px; transition:width 0.6s ease, background 0.6s ease; }

    /* ── History banners ─────────────────────────────── */
    .summary-banner {
        background:var(--surface); border:1px solid var(--border);
        border-radius:10px; padding:14px 16px;
        flex-shrink:0; box-shadow:var(--shadow-sm);
    }
    .banner-row { display:flex; }
    .banner-cell { flex:1; padding:0 14px; }
    .banner-cell:first-child { padding-left:0; }
    .banner-cell:not(:last-child) { border-right:1px solid var(--border); }
    .banner-cell .bp {
        font-size:10px; color:var(--text-muted);
        text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;
    }
    .banner-cell .bv { font-family:var(--serif); font-size:26px; line-height:1.1; }

    .history-left { overflow-y:auto; }
    .history-left::-webkit-scrollbar { width:3px; }
    .history-left::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }

    /* ══ HEATMAP ══════════════════════════════════════ */
    .heatmap-root {
        width:100%; overflow-x:auto; padding-bottom:4px;
    }
    .heatmap-root::-webkit-scrollbar { height:4px; }
    .heatmap-root::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }

    .hm-body {
        display:flex; gap:0; align-items:flex-start;
    }

    /* Day-of-week labels on the left */
    .hm-day-col {
        display:flex; flex-direction:column;
        padding-top:18px; /* offset for month labels row */
        margin-right:6px; flex-shrink:0;
    }
    .hm-day-col span {
        height:13px; line-height:13px; margin-bottom:2px;
        font-size:9px; color:var(--text-muted);
        text-align:right; white-space:nowrap;
    }

    /* Week columns container */
    .hm-weeks {
        display:flex; gap:2px; flex-shrink:0;
    }

    /* Single week column */
    .hm-week {
        display:flex; flex-direction:column; gap:2px;
    }

    /* Month label above week */
    .hm-month-lbl {
        height:16px; line-height:16px;
        font-size:9px; font-weight:600;
        color:var(--text-muted); letter-spacing:0.04em;
        white-space:nowrap; overflow:visible;
    }

    /* Single day cell */
    .hm-cell {
        width:11px; height:11px;
        border-radius:2px;
        cursor:default;
        transition:transform 0.1s;
        flex-shrink:0;
    }
    .hm-cell:hover { transform:scale(1.35); z-index:10; position:relative; }

    /* Legend */
    .hm-legend {
        display:flex; align-items:center; gap:4px;
        margin-top:10px; justify-content:flex-end;
    }
    .hm-legend span {
        font-size:10px; color:var(--text-muted); margin:0 2px;
    }
    .hm-legend .hm-cell { cursor:default; }
    .hm-legend .hm-cell:hover { transform:none; }
</style>
</head>
<body>

<!-- ── Header ────────────────────────────────────────────── -->
<div class="header">
    <div class="header-left">
        <div class="logo-leaf">
            <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 2C16 2 4 8 4 18C4 24.627 9.373 30 16 30C22.627 30 28 24.627 28 18C28 8 16 2 16 2Z" fill="#7BC242"/>
                <path d="M16 30V14" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
                <path d="M16 20C16 20 10 16 10 11" stroke="white" stroke-width="1.2" stroke-linecap="round"/>
                <path d="M16 17C16 17 21 14 22 10" stroke="white" stroke-width="1.2" stroke-linecap="round"/>
            </svg>
        </div>
        <div class="brand-block">
            <div class="brand-name">Society Stores<sup>®</sup></div>
            <div class="brand-tag">We Pamper You Since 1969</div>
        </div>
    </div>
    <div class="header-center">Store Intelligence Dashboard</div>
    <div class="header-right">
        <span class="est-pill">EST. 1969</span>
        <span class="clock" id="clock">--:--:--</span>
    </div>
</div>

<!-- ── Tabs ──────────────────────────────────────────────── -->
<div class="tabs">
    <div class="tab active" onclick="switchTab('live')">Live Feed</div>
    <div class="tab"        onclick="switchTab('today')">Today</div>
    <div class="tab"        onclick="switchTab('history')">History</div>
</div>

<!-- ══ TAB 1: LIVE ══════════════════════════════════════════ -->
<div class="tab-content active" id="tab-live">
    <div class="panel-layout">
        <div class="left-col" style="flex:7;">
            <div class="camera-box">
                <img src="/video_feed" alt="Live feed"/>
                <div class="cam-badge badge-live">● LIVE</div>
                <div class="cam-badge badge-cam">CAM 01 — Entry</div>
                <div class="cam-overlay">
                    <span class="c-green"  id="ov-in">IN: —</span>
                    <span class="c-orange" id="ov-out">OUT: —</span>
                    <span class="c-occ"    id="ov-occ">OCC: —</span>
                </div>
            </div>
            <div class="gauge-wrap">
                <div class="gauge-labels">
                    <span>Store occupancy</span>
                    <span id="gauge-text">— / {{ max_capacity }}</span>
                </div>
                <div class="gauge-track">
                    <div class="gauge-fill" id="gauge-fill" style="width:0%"></div>
                </div>
            </div>
        </div>
        <div class="right-col" style="flex:3;">
            <div class="section-label">Live stats</div>
            <div class="card card-in">
                <div class="card-label">Total in — today</div>
                <div class="card-value c-green" id="live-in">—</div>
            </div>
            <div class="card card-out">
                <div class="card-label">Total out — today</div>
                <div class="card-value c-orange" id="live-out">—</div>
            </div>
            <div class="card card-occ">
                <div class="card-label">Current occupancy</div>
                <div class="card-value c-occ" id="live-occ">—</div>
            </div>
            <div class="card card-peak">
                <div class="card-label">Peak occupancy</div>
                <div class="card-value c-muted" id="live-peak">—</div>
            </div>
            <div class="peak-card">
                <div class="card-label" style="margin-bottom:10px;">Peak hours today</div>
                <div id="live-peak-list"></div>
            </div>
        </div>
    </div>
</div>

<!-- ══ TAB 2: TODAY ══════════════════════════════════════════ -->
<div class="tab-content" id="tab-today">
    <div class="panel-layout">
        <div class="left-col" style="flex:7;">
            <div class="chart-card" style="flex:1; min-height:0;">
                <div class="chart-title">Hourly footfall — today</div>
                <div class="chart-wrap" style="flex:1; height:auto;">
                    <canvas id="hourlyChart"></canvas>
                </div>
            </div>
        </div>
        <div class="right-col" style="flex:3;">
            <div class="section-label">Today's summary</div>
            <div class="stat-grid">
                <div class="card card-in">
                    <div class="card-label">Total in</div>
                    <div class="card-value c-green" id="today-in">—</div>
                </div>
                <div class="card card-out">
                    <div class="card-label">Total out</div>
                    <div class="card-value c-orange" id="today-out">—</div>
                </div>
                <div class="card card-occ">
                    <div class="card-label">Occupancy now</div>
                    <div class="card-value c-occ" id="today-occ">—</div>
                </div>
                <div class="card card-peak">
                    <div class="card-label">Peak occupancy</div>
                    <div class="card-value c-muted" id="today-peak">—</div>
                </div>
            </div>
            <div class="peak-card" style="flex:1;">
                <div class="card-label" style="margin-bottom:10px;">Top peak hours</div>
                <div id="today-peak-list"></div>
            </div>
        </div>
    </div>
</div>

<!-- ══ TAB 3: HISTORY ════════════════════════════════════════ -->
<div class="tab-content" id="tab-history">
    <div class="panel-layout">
        <!-- Left: charts + heatmap -->
        <div class="left-col history-left" style="flex:6; overflow-y:auto;">

            <!-- 7-day bar chart -->
            <div class="chart-card">
                <div class="chart-title">Last 7 days — daily visitors</div>
                <div class="chart-wrap"><canvas id="weeklyChart"></canvas></div>
            </div>

            <!-- Heatmap replacing monthly bar chart -->
            <div class="chart-card">
                <div class="chart-title">Visitor heatmap — <span id="hm-year"></span></div>
                <div class="heatmap-root" id="heatmapRoot">
                    <div style="color:var(--text-dim);font-size:12px;padding:8px">
                        Loading heatmap...
                    </div>
                </div>
            </div>

            <!-- Day of week chart -->
            <div class="chart-card">
                <div class="chart-title">Average visitors by day of week</div>
                <div class="chart-wrap"><canvas id="dowChart"></canvas></div>
            </div>

        </div>

        <!-- Right: summary banners + busiest days -->
        <div class="right-col" style="flex:4;">
            <div class="section-label">Weekly summary</div>
            <div class="summary-banner">
                <div class="banner-row">
                    <div class="banner-cell">
                        <div class="bp">Last 7 days — IN</div>
                        <div class="bv c-green"  id="week-in">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">Last 7 days — OUT</div>
                        <div class="bv c-orange" id="week-out">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">Peak occupancy</div>
                        <div class="bv c-muted"  id="week-peak">—</div>
                    </div>
                </div>
            </div>

            <div class="section-label">Monthly summary</div>
            <div class="summary-banner">
                <div class="banner-row">
                    <div class="banner-cell">
                        <div class="bp" id="month-label">This month — IN</div>
                        <div class="bv c-green"  id="month-in">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">This month — OUT</div>
                        <div class="bv c-orange" id="month-out">—</div>
                    </div>
                    <div class="banner-cell">
                        <div class="bp">Peak occupancy</div>
                        <div class="bv c-muted"  id="month-peak">—</div>
                    </div>
                </div>
            </div>

            <div class="section-label">Busiest days</div>
            <div class="peak-card" style="flex:1;">
                <div class="card-label" style="margin-bottom:10px;">Avg visitors per day of week</div>
                <div id="dow-list"></div>
            </div>
        </div>
    </div>
</div>

<script>
const MAX_CAP = {{ max_capacity }};
let charts = {};
let activeTab = 'live';

// ── Clock ──────────────────────────────────────────────
function tick() {
    document.getElementById('clock').textContent =
        new Date().toLocaleTimeString('en-IN', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}
setInterval(tick, 1000); tick();

// ── Tab switch ─────────────────────────────────────────
function switchTab(name) {
    activeTab = name;
    document.querySelectorAll('.tab').forEach((t,i) =>
        t.classList.toggle('active', ['live','today','history'][i] === name));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-'+name).classList.add('active');
    setTimeout(fetchAll, 60);
}

// ── Chart options ──────────────────────────────────────
const CHART_OPTS = {
    responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ labels:{ color:'#8a9e8a', boxWidth:10, font:{size:10, family:'DM Sans'} } } },
    scales:{
        x:{ ticks:{color:'#b5c4b5', font:{size:9}}, grid:{color:'rgba(0,0,0,0.04)'} },
        y:{ ticks:{color:'#b5c4b5', font:{size:9}}, grid:{color:'rgba(0,0,0,0.06)'}, beginAtZero:true }
    }
};
function makeOrUpdate(id, type, labels, datasets) {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    if (charts[id]) { charts[id].data.labels=labels; charts[id].data.datasets=datasets; charts[id].update(); return; }
    charts[id] = new Chart(ctx, { type, data:{labels,datasets}, options:CHART_OPTS });
}

// ── Gauge ──────────────────────────────────────────────
function updateGauge(occ) {
    const pct  = Math.min(100, Math.round(occ / MAX_CAP * 100));
    const fill = document.getElementById('gauge-fill');
    fill.style.width      = pct + '%';
    fill.style.background = pct < 60 ? '#7BC242' : pct < 85 ? '#e9b824' : '#F28C18';
    document.getElementById('gauge-text').textContent = occ + ' / ' + MAX_CAP;
}

// ── Peak list ──────────────────────────────────────────
function peakHTML(rows, empty) {
    if (!rows || !rows.length)
        return `<div style="color:var(--text-dim);font-size:12px;padding:8px">${empty}</div>`;
    return rows.map((r,i) => `
        <div class="peak-row">
            <span class="peak-hr">#${i+1} &nbsp; ${r.hour.split(' ')[1]}:00</span>
            <span class="peak-vis">${r.count_in} visitors</span>
        </div>`).join('');
}

// ══ HEATMAP RENDERER ══════════════════════════════════
function getHeatColor(count, maxVal) {
    // Society Stores green scale — 5 levels
    if (!count || count === 0) return '#eef5e7';       // empty — very light green
    const ratio = count / maxVal;
    if (ratio < 0.20) return '#c8e69e';                // level 1 — light green
    if (ratio < 0.40) return '#97cc5a';                // level 2 — medium green
    if (ratio < 0.65) return '#7BC242';                // level 3 — brand green
    if (ratio < 0.85) return '#5a9130';                // level 4 — dark green
    return '#3a6020';                                   // level 5 — very dark green
}

function renderHeatmap(hmData) {
    const container = document.getElementById('heatmapRoot');
    if (!container) return;

    const year    = hmData.year;
    const data    = hmData.data;     // {"2026-05-17": 13, ...}
    const maxVal  = hmData.max_count || 1;
    const today   = new Date();

    document.getElementById('hm-year').textContent = year;

    // Month names for labels
    const MONTHS   = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    // Day labels (Mon–Sun), we show Mon / Wed / Fri like GitHub
    const DAY_LBLS = ['Mon','','Wed','','Fri','',''];

    // Build calendar: start from Monday of the week containing Jan 1
    const jan1    = new Date(year, 0, 1);
    const jan1Dow = (jan1.getDay() + 6) % 7; // Mon=0 ... Sun=6
    const start   = new Date(jan1);
    start.setDate(jan1.getDate() - jan1Dow);

    // Build array of week columns
    const weeks = [];
    const cur   = new Date(start);

    while (true) {
        const week = [];
        for (let d = 0; d < 7; d++) {
            const y = cur.getFullYear();
            const m = cur.getMonth();
            const dd = cur.getDate();
            const iso = `${y}-${String(m+1).padStart(2,'0')}-${String(dd).padStart(2,'0')}`;
            const inYear   = y === year;
            const isFuture = cur > today;
            week.push({
                iso, month:m, day:dd,
                count: (inYear && !isFuture) ? (data[iso] || 0) : null,
                inYear
            });
            cur.setDate(cur.getDate() + 1);
        }
        weeks.push(week);
        if (cur.getFullYear() > year) break;
    }

    // Find first week column for each month (for labels)
    const monthFirstWeek = new Array(12).fill(null);
    weeks.forEach((wk, wi) => {
        wk.forEach(cell => {
            if (cell.inYear && cell.day <= 7) {
                const m = cell.month;
                if (monthFirstWeek[m] === null) monthFirstWeek[m] = wi;
            }
        });
    });

    // ── Build HTML ──
    let html = '<div class="hm-body">';

    // Day-of-week labels column
    html += '<div class="hm-day-col">';
    DAY_LBLS.forEach(lbl => {
        html += `<span>${lbl}</span>`;
    });
    html += '</div>';

    // Week columns
    html += '<div class="hm-weeks">';
    weeks.forEach((wk, wi) => {
        html += '<div class="hm-week">';

        // Month label (show only for first week of month)
        const mIdx = monthFirstWeek.findIndex((fw, m) => fw === wi);
        html += `<div class="hm-month-lbl">${mIdx >= 0 ? MONTHS[mIdx] : ''}</div>`;

        // 7 day cells
        wk.forEach(cell => {
            if (!cell.inYear) {
                // Outside current year — render invisible spacer
                html += `<div class="hm-cell" style="background:transparent;"></div>`;
            } else if (cell.count === null) {
                // Future date
                html += `<div class="hm-cell" style="background:#f5f4f0;"></div>`;
            } else {
                const color = getHeatColor(cell.count, maxVal);
                const tip   = cell.count > 0
                    ? `${cell.iso}: ${cell.count} visitors`
                    : `${cell.iso}: no data`;
                html += `<div class="hm-cell" style="background:${color};" title="${tip}"></div>`;
            }
        });

        html += '</div>'; // hm-week
    });
    html += '</div>'; // hm-weeks
    html += '</div>'; // hm-body

    // Legend
    const levels = ['#eef5e7','#c8e69e','#97cc5a','#7BC242','#3a6020'];
    html += '<div class="hm-legend">';
    html += '<span>Less</span>';
    levels.forEach(c => {
        html += `<div class="hm-cell" style="background:${c};border:1px solid rgba(0,0,0,0.08);"></div>`;
    });
    html += '<span>More</span>';
    html += '</div>';

    container.innerHTML = html;
}

// ── Fetch: LIVE ────────────────────────────────────────
async function fetchLive() {
    const s   = await fetch('/api/summary').then(r=>r.json());
    const occ = Math.max(0, s.total_in - s.total_out);
    document.getElementById('live-in').textContent   = s.total_in;
    document.getElementById('live-out').textContent  = s.total_out;
    document.getElementById('live-occ').textContent  = occ;
    document.getElementById('live-peak').textContent = s.peak_occupancy;
    document.getElementById('ov-in').textContent     = 'IN: '  + s.total_in;
    document.getElementById('ov-out').textContent    = 'OUT: ' + s.total_out;
    document.getElementById('ov-occ').textContent    = 'OCC: ' + occ;
    updateGauge(occ);
    const p = await fetch('/api/peaks').then(r=>r.json());
    document.getElementById('live-peak-list').innerHTML = peakHTML(p, 'No data yet');
}

// ── Fetch: TODAY ───────────────────────────────────────
async function fetchToday() {
    const s   = await fetch('/api/summary').then(r=>r.json());
    const occ = Math.max(0, s.total_in - s.total_out);
    document.getElementById('today-in').textContent   = s.total_in;
    document.getElementById('today-out').textContent  = s.total_out;
    document.getElementById('today-occ').textContent  = occ;
    document.getElementById('today-peak').textContent = s.peak_occupancy;
    const h = await fetch('/api/hourly').then(r=>r.json());
    makeOrUpdate('hourlyChart','bar',
        h.map(r=>r.hour.split(' ')[1]+':00'),
        [
            { label:'IN',  data:h.map(r=>r.count_in),  backgroundColor:'rgba(123,194,66,0.7)',  borderColor:'#7BC242', borderWidth:1 },
            { label:'OUT', data:h.map(r=>r.count_out), backgroundColor:'rgba(242,140,24,0.7)', borderColor:'#F28C18', borderWidth:1 }
        ]
    );
    const p = await fetch('/api/peaks').then(r=>r.json());
    document.getElementById('today-peak-list').innerHTML = peakHTML(p, 'No data yet');
}

// ── Fetch: HISTORY ─────────────────────────────────────
async function fetchHistory() {
    // Weekly bar chart
    const w = await fetch('/api/weekly').then(r=>r.json());
    document.getElementById('week-in').textContent   = w.total_in;
    document.getElementById('week-out').textContent  = w.total_out;
    document.getElementById('week-peak').textContent = w.peak_occupancy;
    makeOrUpdate('weeklyChart','bar',
        w.daily.map(d=>d.label),
        [
            { label:'IN',  data:w.daily.map(d=>d.count_in),  backgroundColor:'rgba(123,194,66,0.7)',  borderColor:'#7BC242', borderWidth:1 },
            { label:'OUT', data:w.daily.map(d=>d.count_out), backgroundColor:'rgba(242,140,24,0.7)', borderColor:'#F28C18', borderWidth:1 }
        ]
    );

    // Heatmap
    const hm = await fetch('/api/yearly_heatmap').then(r=>r.json());
    renderHeatmap(hm);

    // Monthly summary banner (stats only, no chart)
    const m = await fetch('/api/monthly').then(r=>r.json());
    document.getElementById('month-label').textContent = m.month_label + ' — IN';
    document.getElementById('month-in').textContent    = m.total_in;
    document.getElementById('month-out').textContent   = m.total_out;
    document.getElementById('month-peak').textContent  = m.peak_occupancy;

    // Day of week chart
    const d = await fetch('/api/busiest_days').then(r=>r.json());
    makeOrUpdate('dowChart','bar',
        d.map(x=>x.day),
        [{ label:'Avg visitors', data:d.map(x=>x.avg_visitors), backgroundColor:'rgba(242,140,24,0.65)', borderColor:'#F28C18', borderWidth:1 }]
    );
    const sorted = [...d].sort((a,b)=>b.avg_visitors-a.avg_visitors);
    document.getElementById('dow-list').innerHTML =
        sorted.some(x=>x.avg_visitors>0)
        ? sorted.map((x,i)=>`
            <div class="peak-row">
                <span class="peak-hr">#${i+1} &nbsp; ${x.day}</span>
                <span class="peak-vis">${x.avg_visitors} avg</span>
            </div>`).join('')
        : '<div style="color:var(--text-dim);font-size:12px;padding:8px">Run for a few days to see trends</div>';
}

// ── Main loop ──────────────────────────────────────────
async function fetchAll() {
    try {
        if (activeTab==='live')    await fetchLive();
        if (activeTab==='today')   await fetchToday();
        if (activeTab==='history') await fetchHistory();
    } catch(e) { console.error('Fetch error:', e); }
}
fetchAll();
setInterval(fetchAll, 10000);
</script>
</body>
</html>"""

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML, max_capacity=MAX_CAPACITY)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/summary')
def api_summary():      return jsonify(get_today_summary())

@app.route('/api/hourly')
def api_hourly():       return jsonify(get_hourly_footfall())

@app.route('/api/peaks')
def api_peaks():        return jsonify(get_peak_hours())

@app.route('/api/weekly')
def api_weekly():       return jsonify(get_weekly_summary())

@app.route('/api/monthly')
def api_monthly():      return jsonify(get_monthly_summary())

@app.route('/api/busiest_days')
def api_busiest():      return jsonify(get_busiest_days())

@app.route('/api/yearly_heatmap')
def api_yearly_heatmap(): return jsonify(get_yearly_heatmap())

if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True)