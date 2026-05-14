import supervision as sv


class Tracker:
    def __init__(self):
        self.tracker = sv.ByteTrack(minimum_consecutive_frames=1)

    def update(self, detections, frame_shape):
        """
        Takes raw detections from Detector and returns tracked detections
        with persistent track IDs.
        """
        if len(detections) == 0:
            return []

        # Convert our detection dicts to supervision Detections format
        sv_detections = self._to_sv_detections(detections, frame_shape)

        # Run ByteTrack
        tracked = self.tracker.update_with_detections(sv_detections)

        # Convert back to our format with track IDs added
        results = []
        for i in range(len(tracked)):
            results.append({
                "track_id": int(tracked.tracker_id[i]),
                "bbox": tuple(map(int, tracked.xyxy[i])),
                "confidence": float(tracked.confidence[i]),
                "class_id": int(tracked.class_id[i])
            })

        return results

    def _to_sv_detections(self, detections, frame_shape):
        import numpy as np

        xyxy       = np.array([d["bbox"] for d in detections], dtype=float)
        confidence = np.array([d["confidence"] for d in detections], dtype=float)
        class_ids  = np.array([d["class_id"] for d in detections], dtype=int)

        return sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_ids
        )