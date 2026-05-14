class TripwireCounter:
    def __init__(self, line_start, line_end):
        """
        line_start: (x1, y1) — start point of virtual line
        line_end:   (x2, y2) — end point of virtual line
        
        For a horizontal line across a door:
            line_start = (0, y)
            line_end   = (frame_width, y)
        
        Crossing top-to-bottom = IN
        Crossing bottom-to-top = OUT
        """
        self.line_start = line_start
        self.line_end   = line_end

        self.count_in   = 0
        self.count_out  = 0

        # Stores last known Y centroid per track ID
        self.prev_centroids = {}

        # Track IDs that already crossed — prevent double counting
        self.crossed_ids = set()

    def _get_centroid(self, bbox):
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _is_crossing(self, prev_y, curr_y, line_y):
        """Check if centroid crossed the horizontal line between frames."""
        crossed_down = prev_y < line_y and curr_y >= line_y  # IN
        crossed_up   = prev_y > line_y and curr_y <= line_y  # OUT
        return crossed_down, crossed_up

    def update(self, tracks):
        """
        Call this every frame with current tracked persons (staff already removed).
        Returns (count_in, count_out, net_occupancy)
        """
        # Use horizontal line Y value (works for doors with horizontal tripwire)
        line_y = self.line_start[1]

        for track in tracks:
            track_id = track["track_id"]
            cx, cy   = self._get_centroid(track["bbox"])

            if track_id in self.prev_centroids:
                prev_cy = self.prev_centroids[track_id]

                # Only count each ID once
                if track_id not in self.crossed_ids:
                    crossed_down, crossed_up = self._is_crossing(prev_cy, cy, line_y)

                    if crossed_down:
                        self.count_in += 1
                        self.crossed_ids.add(track_id)
                        print(f"[Counter] Track {track_id} → IN  | Total IN: {self.count_in}")

                    elif crossed_up:
                        self.count_out += 1
                        self.crossed_ids.add(track_id)
                        print(f"[Counter] Track {track_id} → OUT | Total OUT: {self.count_out}")

            # Update last known position
            self.prev_centroids[track_id] = cy

        return self.count_in, self.count_out, self.net_occupancy()

    def net_occupancy(self):
        return max(0, self.count_in - self.count_out)

    def reset(self):
        self.count_in  = 0
        self.count_out = 0
        self.prev_centroids.clear()
        self.crossed_ids.clear()