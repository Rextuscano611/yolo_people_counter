import cv2

def draw_frame(frame, tracks, staff_ids, count_in, count_out, occupancy, line_start, line_end):
    frame = frame.copy()

    # Draw tripwire line
    cv2.line(frame, line_start, line_end, (0, 255, 255), 2)
    cv2.putText(frame, "TRIPWIRE", (line_start[0] + 5, line_start[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Draw each track
    for t in tracks:
        x1, y1, x2, y2 = t["bbox"]
        tid = t["track_id"]

        if tid in staff_ids:
            color = (0, 128, 0)   # green = staff
            label = f"STAFF {tid}"
        else:
            color = (255, 100, 0) # blue = customer
            label = f"ID {tid}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Draw centroid dot
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        cv2.circle(frame, (cx, cy), 4, color, -1)

    # Draw counter panel (top left)
    cv2.rectangle(frame, (0, 0), (220, 80), (0, 0, 0), -1)
    cv2.putText(frame, f"IN      : {count_in}",  (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0),   2)
    cv2.putText(frame, f"OUT     : {count_out}", (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255),   2)
    cv2.putText(frame, f"OCCUPANCY: {occupancy}",(10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    return frame