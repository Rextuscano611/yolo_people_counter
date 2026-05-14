import cv2
from utils.stream import StreamReader
from core.detector import Detector
from core.tracker import Tracker
from core.staff_filter import StaffFilter
from core.counter import TripwireCounter
from utils.visualizer import draw_frame
from analytics.database import init_db, log_event, update_hourly
from config.settings import SOURCE

FRAME_WIDTH  = 640
FRAME_HEIGHT = 360
LINE_Y       = 240

line_start = (0,           LINE_Y)
line_end   = (FRAME_WIDTH, LINE_Y)

# Init DB on startup
init_db()

stream       = StreamReader(SOURCE)
detector     = Detector()
tracker      = Tracker()
staff_filter = StaffFilter()
counter      = TripwireCounter(line_start, line_end)

stream.start()
detector.load()

frame_num = 0

for frame in stream:
    detections = detector.detect(frame)
    tracks     = tracker.update(detections, frame.shape)

    customer_tracks = [
        t for t in tracks
        if not staff_filter.is_staff(t["track_id"], frame, t["bbox"])
    ]

    prev_in  = counter.count_in
    prev_out = counter.count_out

    count_in, count_out, occupancy = counter.update(customer_tracks)

    # Log new IN events
    if count_in > prev_in:
        for t in customer_tracks:
            if t["track_id"] in counter.crossed_ids:
                log_event("IN", t["track_id"])

    # Log new OUT events
    if count_out > prev_out:
        for t in customer_tracks:
            if t["track_id"] in counter.crossed_ids:
                log_event("OUT", t["track_id"])

    # Update hourly stats every 50 frames
    if frame_num % 50 == 0:
        update_hourly(count_in, count_out, occupancy)

    # Draw
    annotated = draw_frame(
        frame, tracks, staff_filter.staff_ids,
        count_in, count_out, occupancy,
        line_start, line_end
    )

    cv2.imshow("People Counter", annotated)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

    frame_num += 1

# Final DB update on exit
update_hourly(count_in, count_out, occupancy)

stream.stop()
cv2.destroyAllWindows()
print(f"Final → IN: {count_in} | OUT: {count_out} | Occupancy: {occupancy}")

# Print today's summary
from analytics.aggregator import get_today_summary, get_peak_hours
summary = get_today_summary()
print(f"Today → Total IN: {summary['total_in']} | Total OUT: {summary['total_out']} | Peak Occupancy: {summary['peak_occupancy']}")
print(f"Peak hours: {get_peak_hours()}")