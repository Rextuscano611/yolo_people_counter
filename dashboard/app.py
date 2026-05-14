import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))




from flask import Flask, render_template_string, jsonify
from analytics.aggregator import get_hourly_footfall, get_peak_hours, get_today_summary

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Store People Counter</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; }
        h1   { text-align: center; margin-bottom: 24px; color: #38bdf8; font-size: 24px; }

        .cards {
            display: flex; gap: 16px; justify-content: center; margin-bottom: 32px;
        }
        .card {
            background: #1e293b; border-radius: 12px; padding: 24px 32px;
            text-align: center; min-width: 160px;
        }
        .card .value { font-size: 42px; font-weight: bold; }
        .card .label { font-size: 13px; color: #94a3b8; margin-top: 4px; }
        .in    .value { color: #4ade80; }
        .out   .value { color: #f87171; }
        .occ   .value { color: #facc15; }

        .chart-box {
            background: #1e293b; border-radius: 12px;
            padding: 24px; margin-bottom: 24px;
        }
        .chart-box h2 { margin-bottom: 16px; font-size: 16px; color: #94a3b8; }

        .peak-list { list-style: none; }
        .peak-list li {
            background: #0f172a; border-radius: 8px;
            padding: 10px 16px; margin-bottom: 8px;
            display: flex; justify-content: space-between;
        }
        .peak-list li span { color: #38bdf8; font-weight: bold; }

        .refresh { 
            text-align: center; margin-top: 16px;
            font-size: 12px; color: #475569;
        }
    </style>
</head>
<body>
    <h1>🛒 Store People Counter — Live Dashboard</h1>

    <!-- Summary cards -->
    <div class="cards">
        <div class="card in">
            <div class="value" id="total-in">—</div>
            <div class="label">Total IN (today)</div>
        </div>
        <div class="card out">
            <div class="value" id="total-out">—</div>
            <div class="label">Total OUT (today)</div>
        </div>
        <div class="card occ">
            <div class="value" id="peak-occ">—</div>
            <div class="label">Peak Occupancy</div>
        </div>
    </div>

    <!-- Hourly chart -->
    <div class="chart-box">
        <h2>Hourly Footfall</h2>
        <canvas id="footfallChart" height="80"></canvas>
    </div>

    <!-- Peak hours -->
    <div class="chart-box">
        <h2>Top Peak Hours</h2>
        <ul class="peak-list" id="peak-list"></ul>
    </div>

    <div class="refresh">Auto-refreshes every 30 seconds</div>

<script>
let chart = null;

async function fetchData() {
    // Summary
    const s = await fetch('/api/summary').then(r => r.json());
    document.getElementById('total-in').textContent  = s.total_in;
    document.getElementById('total-out').textContent = s.total_out;
    document.getElementById('peak-occ').textContent  = s.peak_occupancy;

    // Hourly chart
    const h = await fetch('/api/hourly').then(r => r.json());
    const labels = h.map(r => r.hour.split(' ')[1] + ':00');
    const inData = h.map(r => r.count_in);
    const outData = h.map(r => r.count_out);

    if (chart) {
        chart.data.labels        = labels;
        chart.data.datasets[0].data = inData;
        chart.data.datasets[1].data = outData;
        chart.update();
    } else {
        chart = new Chart(document.getElementById('footfallChart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'IN',
                        data: inData,
                        backgroundColor: 'rgba(74, 222, 128, 0.7)'
                    },
                    {
                        label: 'OUT',
                        data: outData,
                        backgroundColor: 'rgba(248, 113, 113, 0.7)'
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#e2e8f0' } } },
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
                }
            }
        });
    }

    // Peak hours
    const p = await fetch('/api/peaks').then(r => r.json());
    const list = document.getElementById('peak-list');
    list.innerHTML = p.map((r, i) =>
        `<li>#${i+1} &nbsp; ${r.hour}:00 <span>${r.count_in} visitors</span></li>`
    ).join('');
}

fetchData();
setInterval(fetchData, 30000);
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

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
    app.run(debug=False, port=5000)