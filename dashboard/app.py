import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, jsonify, Response
from analytics.aggregator import get_hourly_footfall, get_peak_hours, get_today_summary
import cv2
import threading

app = Flask(__name__)

# Shared frame buffer — main.py writes here, dashboard reads it
frame_buffer = {"frame": None, "lock": threading.Lock()}

def set_frame(frame):
    with frame_buffer["lock"]:
        frame_buffer["frame"] = frame.copy()

import time 

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
    <title>Store People Counter</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 12px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        h1 {
            text-align: center;
            color: #38bdf8;
            font-size: 18px;
            margin-bottom: 12px;
        }
        .layout {
            display: flex;
            gap: 12px;
            flex: 1;
            overflow: hidden;
        }

        /* LEFT 70% */
        .left {
            flex: 7;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .camera-box {
            flex: 1;
            background: #000;
            border-radius: 12px;
            border: 1px solid #1e293b;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .camera-box img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .badge-live {
            position: absolute; top: 10px; left: 10px;
            background: #e24b4a; color: #fff;
            font-size: 11px; padding: 3px 8px;
            border-radius: 4px; font-weight: 500;
        }
        .badge-cam {
            position: absolute; top: 10px; right: 10px;
            background: rgba(0,0,0,0.6); color: #ccc;
            font-size: 11px; padding: 3px 8px; border-radius: 4px;
        }
        .counter-overlay {
            position: absolute; bottom: 10px; left: 10px;
            background: rgba(0,0,0,0.7);
            border-radius: 8px; padding: 8px 14px;
            display: flex; gap: 16px;
        }
        .counter-overlay span { font-size: 13px; font-weight: 500; }
        .c-in  { color: #4ade80; }
        .c-out { color: #f87171; }
        .c-occ { color: #facc15; }

        .chart-box {
            background: #1e293b; border-radius: 12px;
            padding: 12px 16px;
        }
        .chart-box p {
            font-size: 12px; color: #94a3b8; margin-bottom: 8px;
        }

        /* RIGHT 30% */
        .right {
            flex: 3;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .section-title {
            font-size: 13px; font-weight: 500;
            color: #94a3b8; padding: 2px 0;
        }
        .stat-card {
            background: #1e293b; border-radius: 12px;
            padding: 14px 16px;
        }
        .stat-card .label {
            font-size: 11px; color: #64748b; margin-bottom: 4px;
        }
        .stat-card .value {
            font-size: 28px; font-weight: 500;
        }
        .peak-box {
            background: #1e293b; border-radius: 12px;
            padding: 14px 16px; flex: 1;
        }
        .peak-box .label {
            font-size: 11px; color: #64748b; margin-bottom: 10px;
        }
        .peak-row {
            display: flex; justify-content: space-between;
            align-items: center; margin-bottom: 8px;
        }
        .peak-row .hour { font-size: 13px; color: #e2e8f0; }
        .peak-row .visitors { font-size: 12px; font-weight: 500; color: #38bdf8; }
    </style>
</head>
<body>
    <h1>🛒 Store People Counter — Live Dashboard</h1>

    <div class="layout">

        <!-- LEFT: camera + chart -->
        <div class="left">
            <div class="camera-box">
                <img src="/video_feed" alt="Live camera feed" />
                <div class="badge-live">● LIVE</div>
                <div class="badge-cam">CAM 01 — Entry</div>
                <div class="counter-overlay">
                    <span class="c-in"  id="ov-in">IN: —</span>
                    <span class="c-out" id="ov-out">OUT: —</span>
                    <span class="c-occ" id="ov-occ">OCC: —</span>
                </div>
            </div>

            <div class="chart-box">
                <p>Hourly footfall — today</p>
                <canvas id="footfallChart" height="55"></canvas>
            </div>
        </div>

        <!-- RIGHT: stats -->
        <div class="right">
            <p class="section-title">Store analytics</p>

            <div class="stat-card">
                <div class="label">Total in (today)</div>
                <div class="value c-in" id="total-in">—</div>
            </div>

            <div class="stat-card">
                <div class="label">Total out (today)</div>
                <div class="value c-out" id="total-out">—</div>
            </div>

            <div class="stat-card">
                <div class="label">Current occupancy</div>
                <div class="value c-occ" id="occupancy">—</div>
            </div>

            <div class="stat-card">
                <div class="label">Peak occupancy</div>
                <div class="value" style="color:#e2e8f0;" id="peak-occ">—</div>
            </div>

            <div class="peak-box">
                <div class="label">Top peak hours</div>
                <div id="peak-list"></div>
            </div>
        </div>

    </div>

<script>
let chart = null;

async function fetchData() {
    const s = await fetch('/api/summary').then(r => r.json());
    document.getElementById('total-in').textContent  = s.total_in;
    document.getElementById('total-out').textContent = s.total_out;
    document.getElementById('occupancy').textContent = s.total_in - s.total_out;
    document.getElementById('peak-occ').textContent  = s.peak_occupancy;
    document.getElementById('ov-in').textContent  = 'IN: '  + s.total_in;
    document.getElementById('ov-out').textContent = 'OUT: ' + s.total_out;
    document.getElementById('ov-occ').textContent = 'OCC: ' + Math.max(0, s.total_in - s.total_out);

    const h = await fetch('/api/hourly').then(r => r.json());
    const labels  = h.map(r => r.hour.split(' ')[1] + ':00');
    const inData  = h.map(r => r.count_in);
    const outData = h.map(r => r.count_out);

    if (chart) {
        chart.data.labels = labels;
        chart.data.datasets[0].data = inData;
        chart.data.datasets[1].data = outData;
        chart.update();
    } else {
        chart = new Chart(document.getElementById('footfallChart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'IN',  data: inData,  backgroundColor: 'rgba(74,222,128,0.7)' },
                    { label: 'OUT', data: outData, backgroundColor: 'rgba(248,113,113,0.7)' }
                ]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
                scales: {
                    x: { ticks: { color: '#64748b' }, grid: { color: '#0f172a' } },
                    y: { ticks: { color: '#64748b' }, grid: { color: '#334155' } }
                }
            }
        });
    }

    const p = await fetch('/api/peaks').then(r => r.json());
    document.getElementById('peak-list').innerHTML = p.map((r, i) =>
        `<div class="peak-row">
            <span class="hour">#${i+1} &nbsp; ${r.hour.split(' ')[1]}:00</span>
            <span class="visitors">${r.count_in} visitors</span>
        </div>`
    ).join('');
}

fetchData();
setInterval(fetchData, 10000);
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/summary')
def api_summary():
    return jsonify(get_today_summary())

@app.route('/api/hourly')
def api_hourly():
    return jsonify(get_hourly_footfall())

@app.route('/api/peaks')
def api_peaks():
    return jsonify(get_peak_hours())


if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True)