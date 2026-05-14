from ultralytics import YOLO
from config.settings import MODEL_PATH, DEVICE, CONFIDENCE_THRESHOLD, PERSON_CLASS_ID
import os

class Detector:
    def __init__(self):
        self.model = None

    def load(self):
        # Auto download model if not present in models/ folder
        if not os.path.exists(MODEL_PATH):
            print(f"[Detector] Model not found at {MODEL_PATH}, downloading...")
        
        self.model = YOLO(MODEL_PATH)
        print(f"[Detector] Loaded: {MODEL_PATH} on device: {DEVICE}")

    def detect(self, frame):
        """
        Run detection on a single frame.
        Returns list of detections: each is a dict with bbox, confidence, class_id
        """
        results = self.model(
            frame,
            device=DEVICE,
            conf=CONFIDENCE_THRESHOLD,
            classes=[PERSON_CLASS_ID],  # only detect persons
            verbose=False               # suppress per-frame console output
        )

        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls  = int(box.cls[0])
                detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf,
                    "class_id": cls
                })

        return detections