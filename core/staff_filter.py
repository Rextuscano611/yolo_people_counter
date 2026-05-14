import cv2
import numpy as np
from config.settings import GREEN_LOWER, GREEN_UPPER, GREEN_THRESHOLD


class StaffFilter:
    def __init__(self):
        # Set of track IDs confirmed as staff — never recheck these
        self.staff_ids = set()

    def _get_torso_crop(self, frame, bbox):
        """Crop top 55% of bounding box = torso/shirt region."""
        x1, y1, x2, y2 = bbox
        torso_bottom = y1 + int((y2 - y1) * 0.55)

        # Safety clamp to frame boundaries
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame.shape[1], x2)
        torso_bottom = min(frame.shape[0], torso_bottom)

        crop = frame[y1:torso_bottom, x1:x2]
        return crop

    def _is_green(self, crop):
        """Check if crop contains enough green pixels to be staff uniform."""
        if crop is None or crop.size == 0:
            return False

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

        lower = np.array(GREEN_LOWER)
        upper = np.array(GREEN_UPPER)

        mask = cv2.inRange(hsv, lower, upper)
        green_ratio = np.sum(mask > 0) / mask.size

        return green_ratio > GREEN_THRESHOLD

    def is_staff(self, track_id, frame, bbox):
        """
        Returns True if this track ID is staff.
        Once flagged as staff, always returns True without rechecking.
        """
        # Already confirmed staff — skip recheck
        if track_id in self.staff_ids:
            return True

        # First time seeing this ID — run color check
        crop = self._get_torso_crop(frame, bbox)
        if self._is_green(crop):
            self.staff_ids.add(track_id)
            print(f"[StaffFilter] Track ID {track_id} flagged as STAFF")
            return True

        return False

    def reset(self):
        """Clear staff ID buffer — call this at start of new session."""
        self.staff_ids.clear()

    def staff_count(self):
        return len(self.staff_ids)