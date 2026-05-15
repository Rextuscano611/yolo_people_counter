# 🛒 Society Store — People Counter

A real-time people counting system for a grocery store using existing CCTV cameras.
Detects customers entering and exiting, excludes staff by uniform colour, and displays live analytics on a web dashboard.

---

## Features

- Real-time person detection using YOLOv11
- Persistent tracking with ByteTrack (one ID per person across frames)
- Staff exclusion via HSV green uniform detection
- Virtual tripwire counting — IN / OUT / Occupancy
- SQLite logging of every crossing event
- Hourly footfall aggregation and peak hour detection
- Live dashboard with camera feed + Chart.js bar chart
- Interactive tripwire placement via mouse click on first frame
- RTSP and MP4 video source support
- `.env`-driven config — zero code changes between dev and production

---

## Project Structure

```
grocery_people_counter/
│
├── config/
│   ├── __init__.py
│   └── settings.py           # all config loaded from .env
│
├── core/
│   ├── __init__.py
│   ├── detector.py           # YOLOv11 person detection
│   ├── tracker.py            # ByteTrack via supervision
│   ├── staff_filter.py       # HSV green detection + Re-ID buffer
│   └── counter.py            # virtual tripwire IN/OUT logic
│
├── analytics/
│   ├── __init__.py
│   ├── database.py           # SQLite event logging + hourly upsert
│   └── aggregator.py         # hourly footfall, peak hours, today summary
│
├── dashboard/
│   └── app.py                # Flask dashboard — live feed + analytics
│
├── utils/
│   ├── __init__.py
│   ├── stream.py             # RTSP / MP4 reader
│   ├── visualizer.py         # draw boxes, tripwire, counters on frame
│   └── line_selector.py      # interactive tripwire placement UI
│
├── data/
│   ├── videos/               # test .mp4 clips (gitignored)
│   └── db/
│       └── footfall.db       # SQLite database (gitignored)
│
├── models/
│   └── yolo11n.pt            # auto-downloaded by ultralytics (gitignored)
│
├── main.py                   # entry point
├── requirements.txt
├── .env                      # config (gitignored — see .env.example)
└── .gitignore
```

---

## Hardware

| Environment | Device | Model |
|---|---|---|
| Development | Intel i5 (CPU) | YOLOv11n |
| Production | Apple M4 (MPS) | YOLOv11s |

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/your-username/society_store.git
cd society_store
```

### 2. Create and activate virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create `.env` file
Copy the example and fill in your values:
```bash
cp .env.example .env
```

```env
DEVICE=cpu
MODEL=yolo11n.pt
SOURCE=data/videos/test.mp4
GREEN_THRESHOLD=0.18
LINE_Y=0
DB_PATH=data/db/footfall.db
SHOW_WINDOW=1
INVERT_CROSSING=false
```

### 5. Create required directories
```bash
mkdir -p data/db data/videos models
```

### 6. Run
```bash
python main.py
```

Open browser at **http://localhost:5000**

---

## Configuration

All config is managed via `.env` — no code changes needed between environments.

| Variable | Description | Example |
|---|---|---|
| `DEVICE` | Inference device | `cpu` / `mps` / `cuda` |
| `MODEL` | YOLO model filename | `yolo11n.pt` / `yolo11s.pt` |
| `SOURCE` | Video source | `data/videos/test.mp4` or `rtsp://ip/stream` |
| `GREEN_THRESHOLD` | Min green pixel ratio to flag as staff | `0.18` |
| `LINE_Y` | Tripwire Y position in pixels | `0` = interactive selector |
| `DB_PATH` | SQLite database path | `data/db/footfall.db` |
| `SHOW_WINDOW` | Show local cv2 preview window | `1` / `0` |
| `INVERT_CROSSING` | Swap IN/OUT direction | `true` / `false` |

---

## Tripwire Setup

On first run with `LINE_Y=0`:
1. A window opens showing the first camera frame
2. Move mouse to place the line at the door threshold
3. Click to confirm position
4. Press **ENTER** or **SPACE** to start
5. Press **ESC** to use the default value

After calibration, note the printed `LINE_Y` value and set it in `.env` to skip the selector on future runs.

---

## Staff Filtering

Staff are identified by their lime-green uniform (HSV calibrated from real photos):

```python
GREEN_LOWER = (28, 33, 90)
GREEN_UPPER = (65, 147, 255)
```

The filter crops the top 55% of each bounding box (torso region) and checks if green pixels exceed `GREEN_THRESHOLD`. Once flagged, a track ID is permanently suppressed via a Re-ID buffer.

To recalibrate for a different uniform, run the calibration script on new photos and update the values in `config/settings.py`.

---

## Dashboard

The dashboard runs automatically as part of `main.py` on port 5000.

| Route | Description |
|---|---|
| `/` | Main dashboard — live feed + chart |
| `/video_feed` | MJPEG live camera stream |
| `/api/summary` | Today's IN / OUT / occupancy JSON |
| `/api/hourly` | Hourly footfall records JSON |
| `/api/peaks` | Top 3 peak hours JSON |

Auto-refreshes every 10 seconds.

---

## Production Deployment (Apple M4)

Update `.env`:
```env
DEVICE=mps
MODEL=yolo11s.pt
SOURCE=rtsp://camera_ip/stream1
LINE_Y=0
SHOW_WINDOW=0
```

Camera placement: mount above entry/exit door looking straight down. Horizontal tripwire will trigger as people walk toward or away from camera.

---

## Known Issues / TODO

- [ ] ByteTrack deprecation warning (supervision v0.28+) — upgrade to `sv.ByteTrack(minimum_consecutive_frames=1)`
- [ ] Multi-camera support
- [ ] CSV daily report export
- [ ] Email / SMS alert when occupancy exceeds threshold
- [ ] Staff filter not yet tested on live CCTV feed — recalibrate HSV on deployment day

---

## Tech Stack

| Component | Library |
|---|---|
| Detection | [Ultralytics YOLOv11](https://github.com/ultralytics/ultralytics) |
| Tracking | [supervision ByteTrack](https://github.com/roboflow/supervision) |
| Computer Vision | OpenCV |
| Database | SQLite (built-in) |
| Dashboard | Flask + Chart.js |
| Config | python-dotenv |
