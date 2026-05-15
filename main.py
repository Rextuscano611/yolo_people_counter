import cv2
import os
import threading

from dashboard.app import set_frame
from dashboard import app as dashboard_app
from utils.stream import StreamReader
from utils.line_selector import select_line_y
from core.detector import Detector
from core.tracker import Tracker
from core.staff_filter import StaffFilter
from core.counter import TripwireCounter
from utils.visualizer import draw_frame
from analytics.database import init_db, log_event, update_hourly
from config.settings import SOURCE, LINE_Y as ENV_LINE_Y

DEFAULT_LINE_Y = 240

# ── DB + Dashboard ────────────────────────────────────────────────────────────
init_db()

dashboard_thread = threading.Thread(
    target=lambda: dashboard_app.app.run(port=5000, threaded=True),
    daemon=True
)
dashboard_thread.start()
print("[Dashboard] Running at http://localhost:5000")

# ── Stream + Models ───────────────────────────────────────────────────────────
stream       = StreamReader(SOURCE)
detector     = Detector()
tracker      = Tracker()
staff_filter = StaffFilter()

stream.start()
detector.load()

# ── Get ACTUAL frame resolution from stream ───────────────────────────────────
# Do NOT assume 640x360 — RTSP cameras can be 1280x720, 1920x1080, etc.
ACTUAL_W = int(stream.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
ACTUAL_H = int(stream.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"[Config] Actual stream resolution: {ACTUAL_W}x{ACTUAL_H}")

# ── LINE_Y selection ──────────────────────────────────────────────────────────
#
# Priority:
#   1. LINE_Y in .env (non-zero)  → use directly (already in actual frame coords)
#   2. SHOW_WINDOW=0 (headless)   → use default
#   3. Otherwise                  → show selector on first frame, scale Y back
#
if ENV_LINE_Y:
    LINE_Y = ENV_LINE_Y
    print(f"[Config] LINE_Y loaded from .env: {LINE_Y}")

elif os.environ.get("SHOW_WINDOW", "1") == "0":
    LINE_Y = DEFAULT_LINE_Y
    print(f"[Config] Headless mode — using default LINE_Y: {LINE_Y}")

else:
    print("[Config] LINE_Y not set — launching interactive selector...")
    first_frame = next(iter(stream), None)

    if first_frame is not None:
        # Choose a display size that fits on screen while keeping aspect ratio
        # Selector always shows at a comfortable size, not the raw camera res
        DISPLAY_W = 960
        DISPLAY_H = int(ACTUAL_H * (DISPLAY_W / ACTUAL_W))
        display_frame = cv2.resize(first_frame, (DISPLAY_W, DISPLAY_H))

        # User clicks on the DISPLAY frame — get Y in display coords
        selected_y_display = select_line_y(
            display_frame,
            default_line_y=int(DEFAULT_LINE_Y * (DISPLAY_H / ACTUAL_H))
        )

        # Scale Y back to ACTUAL frame coordinates
        LINE_Y = int(selected_y_display * (ACTUAL_H / DISPLAY_H))
        print(f"[Config] Selected Y on display: {selected_y_display} → Scaled to actual frame: {LINE_Y}")

    else:
        LINE_Y = DEFAULT_LINE_Y
        print(f"[Config] Stream returned no frames — using default LINE_Y: {LINE_Y}")

# line_start/end now use ACTUAL frame width, not hardcoded 640
line_start = (0,        LINE_Y)
line_end   = (ACTUAL_W, LINE_Y)
print(f"[Config] Tripwire: Y={LINE_Y}  ({line_start} → {line_end})")

# ── Counter ───────────────────────────────────────────────────────────────────
counter = TripwireCounter(line_start, line_end)

# ── Main loop ─────────────────────────────────────────────────────────────────
count_in, count_out, occupancy = 0, 0, 0
frame_num = 0

for frame in stream:
    detections = detector.detect(frame)
    tracks     = tracker.update(detections, frame.shape)



    
    

    customer_tracks = [
        trk for trk in tracks
        if not staff_filter.is_staff(trk["track_id"], frame, trk["bbox"])
    ]

    

    prev_crossed_in  = set(counter.crossed_in_ids)
    prev_crossed_out = set(counter.crossed_out_ids)

    count_in, count_out, occupancy = counter.update(customer_tracks)

    for track_id in (counter.crossed_in_ids  - prev_crossed_in):
        log_event("IN",  track_id)

    for track_id in (counter.crossed_out_ids - prev_crossed_out):
        log_event("OUT", track_id)

    if frame_num % 50 == 0:
        update_hourly(count_in, count_out, occupancy)

    annotated = draw_frame(
        frame, tracks, staff_filter.staff_ids,
        count_in, count_out, occupancy,
        line_start, line_end
    )

    set_frame(annotated)

    if os.environ.get("SHOW_WINDOW", "1") == "1":
        # Resize preview window to fit screen (display only, not processing)
        preview = cv2.resize(annotated, (960, int(ACTUAL_H * 960 / ACTUAL_W)))
        cv2.imshow("People Counter", preview)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    frame_num += 1

# ── Cleanup ───────────────────────────────────────────────────────────────────
update_hourly(count_in, count_out, occupancy)
stream.stop()
cv2.destroyAllWindows()

print(f"Final → IN: {count_in} | OUT: {count_out} | Occupancy: {occupancy}")

from analytics.aggregator import get_today_summary, get_peak_hours
summary = get_today_summary()
print(f"Today → Total IN: {summary['total_in']} | Total OUT: {summary['total_out']} | Peak: {summary['peak_occupancy']}")
print(f"Peak hours: {get_peak_hours()}")